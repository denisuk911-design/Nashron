from core.database import Database


def test_database_creation(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    assert (tmp_path / "roman.sqlite3").exists()


def test_save_and_read_messages(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    conversation_id = db.create_conversation("Тест")
    first_id = db.add_message(conversation_id, "user", "Привет")
    second_id = db.add_message(conversation_id, "roman", "Слышу")
    messages = db.list_messages(conversation_id)
    assert [message.id for message in messages] == [first_id, second_id]
    assert messages[0].content == "Привет"
    assert messages[1].content == "Слышу"


def test_full_conversation_survives_new_database_instance(tmp_path):
    path = tmp_path / "roman.sqlite3"
    db = Database(path)
    db.initialize()
    conversation_id = db.create_conversation("Длинный разговор")
    for idx in range(30):
        db.add_message(conversation_id, "user", f"сообщение {idx}")

    reopened = Database(path)
    reopened.initialize()
    messages = reopened.list_messages(conversation_id)
    assert len(messages) == 30
    assert messages[0].content == "сообщение 0"
    assert messages[-1].content == "сообщение 29"


def test_list_all_messages_across_conversations(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    first = db.create_conversation("Первый")
    second = db.create_conversation("Второй")
    db.add_message(first, "user", "первый диалог")
    db.add_message(second, "roman", "второй диалог")

    messages = db.list_all_messages()
    assert [message.content for message in messages] == ["первый диалог", "второй диалог"]


def test_ensure_single_conversation_creates_default_dialog(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    conversation_id = db.ensure_single_conversation("Roman")

    conversations = db.list_conversations()
    assert conversation_id == conversations[0].id
    assert len(conversations) == 1
    assert conversations[0].title == "Roman"


def test_ensure_single_conversation_merges_existing_dialogs(tmp_path):
    db_path = tmp_path / "roman.sqlite3"
    db = Database(db_path)
    db.initialize()
    first = db.create_conversation("first")
    second = db.create_conversation("second")
    db.add_message(first, "user", "from first")
    db.add_message(second, "roman", "from second")

    conversation_id = db.ensure_single_conversation("Roman")

    assert conversation_id == first
    assert len(db.list_conversations()) == 1
    assert [message.content for message in db.list_messages(conversation_id)] == ["from first", "from second"]
    assert (tmp_path / "roman.before_single_dialog.sqlite3").exists()


def test_memories_are_separate_from_identity(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    memory_id = db.add_memory("Пользователь любит короткие ответы")
    assert db.list_memories()[0].id == memory_id
    db.delete_memory(memory_id)
    assert db.list_memories() == []


def test_save_and_read_petr_messages(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    conversation_id = db.create_conversation("Команда")
    message_id = db.add_message(conversation_id, "petr", "Сделаю через Gemini")
    messages = db.list_messages(conversation_id)
    assert messages[0].id == message_id
    assert messages[0].role == "petr"


def test_save_and_read_dynamic_employee_messages(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    conversation_id = db.create_conversation("Команда")

    message_id = db.add_message(conversation_id, "shushan", "На связи.")

    messages = db.list_messages(conversation_id)
    assert messages[0].id == message_id
    assert messages[0].role == "shushan"


def test_repairs_message_foreign_keys_after_dynamic_role_migration(tmp_path):
    db_path = tmp_path / "roman.sqlite3"
    db = Database(db_path)
    db.initialize()
    conversation_id = db.create_conversation("legacy")
    message_id = db.add_message(conversation_id, "user", "start task")
    db.ensure_project("project-default", "Default Project")

    with db.connect() as conn:
        conn.execute("PRAGMA writable_schema = ON")
        conn.execute(
            """
            UPDATE sqlite_master
            SET sql = REPLACE(sql, 'REFERENCES messages(id)', 'REFERENCES messages_old(id)')
            WHERE type = 'table'
              AND name = 'tasks'
            """
        )
        conn.execute("PRAGMA writable_schema = OFF")
        version = int(conn.execute("PRAGMA schema_version").fetchone()[0])
        conn.execute(f"PRAGMA schema_version = {version + 1}")

    reopened = Database(db_path)
    reopened.initialize()

    with reopened.connect() as conn:
        foreign_keys = conn.execute("PRAGMA foreign_key_list(tasks)").fetchall()
        assert any(row["table"] == "messages" for row in foreign_keys)

    task_id = reopened.create_task("project-default", "after repair", message_id, "1.0")
    assert reopened.get_task(task_id)["owner_message_id"] == message_id


def test_repairs_malformed_orphan_messages_old_schema(tmp_path):
    db_path = tmp_path / "roman.sqlite3"
    db = Database(db_path)
    db.initialize()

    with db.connect() as conn:
        conn.execute("PRAGMA writable_schema = ON")
        conn.execute(
            """
            INSERT INTO sqlite_master(type, name, tbl_name, rootpage, sql)
            VALUES ('table', 'messages_old', 'messages_old', 0, 'CREATE TABLE "messages" (id INTEGER PRIMARY KEY)')
            """
        )
        conn.execute("PRAGMA writable_schema = OFF")
        version = int(conn.execute("PRAGMA schema_version").fetchone()[0])
        conn.execute(f"PRAGMA schema_version = {version + 1}")

    reopened = Database(db_path)
    reopened.initialize()

    with reopened.connect() as conn:
        broken_rows = conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name = 'messages_old'").fetchone()[0]
    assert broken_rows == 0


def test_records_routing_decision(tmp_path):
    db = Database(tmp_path / "roman.sqlite3")
    db.initialize()
    conversation_id = db.create_conversation()
    message_id = db.add_message(conversation_id, "user", "Шушанна, проверь ограничения")

    decision_id = db.record_routing_decision(
        message_id=message_id,
        thread_id=f"conversation-{conversation_id}",
        participation_mode="DIRECT",
        explicit_recipients=["shushan"],
        inferred_recipients=[],
        selected_responders=["shushan"],
        excluded_responders={"roman": "selected_other_employee"},
        interruption_policy=None,
        reason="explicit_name_or_alias",
        router_version="test",
    )

    rows = db.list_routing_decisions()
    assert rows[0]["id"] == decision_id
    assert rows[0]["participation_mode"] == "DIRECT"
    assert "shushan" in rows[0]["selected_responders"]
