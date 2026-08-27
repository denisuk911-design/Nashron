from pathlib import Path

from core.chat_attachment_service import ChatAttachmentService
from core.database import Database


def test_chat_attachment_survives_database_restart_and_binds_message(tmp_path: Path) -> None:
    database_path = tmp_path / "team2050.sqlite3"
    database = Database(database_path)
    database.initialize()
    conversation_id = database.create_conversation("chat")
    source = tmp_path / "board.png"
    source.write_bytes(b"durable-upload")

    service = ChatAttachmentService(database, tmp_path / "workspace")
    attachment = service.import_file(conversation_id, source)
    message_id = database.add_message(conversation_id, "user", "See attachment")
    service.bind_to_message([attachment], message_id)

    restarted = ChatAttachmentService(Database(database_path), tmp_path / "workspace")
    restored = restarted.attachments_for_message(conversation_id, message_id)
    assert restored == [attachment]
    assert restarted.physical_path(restored[0]).read_bytes() == source.read_bytes()
    with database.connect() as conn:
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []


def test_clipboard_bytes_are_not_stored_in_message_text(tmp_path: Path) -> None:
    database = Database(tmp_path / "team2050.sqlite3")
    database.initialize()
    conversation_id = database.create_conversation("chat")
    service = ChatAttachmentService(database, tmp_path / "workspace")

    attachment = service.import_bytes(conversation_id, b"image-content", "clipboard.png")

    assert attachment.is_image
    assert "chat_attachments" in attachment.relative_path
    assert database.list_messages(conversation_id) == []
