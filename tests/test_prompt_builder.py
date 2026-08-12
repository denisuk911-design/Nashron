import json

from core.database import Database
from core.identity_service import IdentityService
from core.management_models import AgentProfile
from core.management_service import ManagementService
from core.config_repository import ConfigurationRepository
from core.prompt_builder import PromptBuilder


def make_builder(tmp_path, limit=20):
    prompt_path = tmp_path / "team_system.md"
    prompt_path.write_text("Системные правила Team2050", encoding="utf-8")
    identity_path = tmp_path / "team_identity.json"
    identity_path.write_text(
        json.dumps(
            {"full_name": "Team2050", "current_year": 2050, "identity_locked": True},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    timeline_path = tmp_path / "team_timeline.json"
    timeline_path.write_text(json.dumps({"events": []}), encoding="utf-8")
    db = Database(tmp_path / "team.sqlite3")
    db.initialize()
    return PromptBuilder(prompt_path, IdentityService(identity_path), timeline_path, db, limit), db


def test_builds_system_context(tmp_path):
    builder, db = make_builder(tmp_path)
    conversation_id = db.create_conversation()
    db.add_memory("Пользователь предпочитает русский язык")
    prompt = builder.build(conversation_id, "Привет")
    assert "Системные правила Team2050" in prompt
    assert "Team2050" in prompt
    assert "2050" in prompt
    assert "Пользователь предпочитает русский язык" in prompt
    assert "Привет" in prompt
    assert "пиши только свою реплику" in prompt
    assert "не вставляй внутри ответа диалог с их именами" in prompt


def test_limits_immediate_history_and_drops_irrelevant_old_messages(tmp_path):
    builder, db = make_builder(tmp_path, limit=2)
    conversation_id = db.create_conversation()
    for idx in range(5):
        db.add_message(conversation_id, "user", f"old-{idx}")
    prompt = builder.build(conversation_id, "new")
    assert "IMMEDIATE CONTEXT" in prompt
    assert "TASK-RELEVANT CONTEXT" in prompt
    assert "old-0" not in prompt
    assert "old-1" not in prompt
    assert "old-3" in prompt
    assert "old-4" in prompt


def test_uses_selected_context_after_single_dialog_migration(tmp_path):
    builder, db = make_builder(tmp_path, limit=2)
    first = db.create_conversation()
    second = db.create_conversation()
    db.add_message(first, "user", "помни первый разговор")
    db.add_message(second, "user", "помни второй разговор")
    conversation_id = db.ensure_single_conversation()

    prompt = builder.build(conversation_id, "что помнишь?")

    assert "CONTEXT SNAPSHOT" in prompt
    assert "помни первый разговор" in prompt
    assert "помни второй разговор" in prompt


def test_local_tools_policy_is_explicit(tmp_path):
    builder, db = make_builder(tmp_path)
    conversation_id = db.create_conversation()
    assert "ЛОКАЛЬНЫЙ ПОМОЩНИК ВЫКЛЮЧЕН" in builder.build(conversation_id, "cmd")
    prompt = builder.build(conversation_id, "cmd", allow_local_tools=True)
    assert "ЛОКАЛЬНЫЙ ПОМОЩНИК ВКЛЮЧЕН" in prompt
    assert "через твой CLI-провайдер" in prompt


def test_prompt_pushes_specific_future_voice(tmp_path):
    builder, db = make_builder(tmp_path)
    conversation_id = db.create_conversation()
    prompt = builder.build(conversation_id, "расскажи про 2049")
    assert "2050" in prompt
    assert "КОНКРЕТИКУ" in prompt
    assert "живо и конкретно" in prompt


def test_builds_dynamic_reviewer_context_with_peer_position(tmp_path):
    builder, db = make_builder(tmp_path)
    service = ManagementService(db, ConfigurationRepository(tmp_path / "management"))
    service.ensure_foundations()
    service.create_agent(
        AgentProfile("agent-designer-fixture", "Максим", "Проектирует изделия", "ACTIVE", "CODEX_CLI"),
        ["DESIGN_ENGINEER"],
        ["CHAT"],
        reason="test",
    )
    service.create_agent(
        AgentProfile("agent-reviewer-fixture", "Олена", "Проверяет результат", "ACTIVE", "GEMINI_CLI"),
        ["QA_ENGINEER"],
        ["CHAT"],
        reason="test",
    )
    conversation_id = db.create_conversation()
    db.add_message(conversation_id, "designer-fixture", "План: Олена проверит расчеты")
    prompt = builder.build(
        conversation_id,
        "Олена, проверь",
        agent_key="reviewer-fixture",
        peer_context="Максим предлагает план",
    )
    assert "Олена" in prompt
    assert "Gemini CLI" in prompt
    assert "Максим предлагает план" in prompt
    assert "Максим: План: Олена проверит расчеты" in prompt


def test_builds_autonomous_goal_context(tmp_path):
    builder, db = make_builder(tmp_path)
    conversation_id = db.create_conversation()

    prompt = builder.build(
        conversation_id,
        "цель: сделать план",
        autonomous_goal="сделать план",
        autonomous_turn=3,
        complete_on_goal=True,
    )

    assert "АВТОСОВЕЩАНИЕ ВКЛЮЧЕНО" in prompt
    assert "Цель/тема: сделать план" in prompt
    assert "Ход обсуждения: 3" in prompt
    assert "AUTO_DONE" in prompt
    assert "Не симулируй ответ второго" in prompt
def test_dynamic_employee_prompt_discourages_nagging_user(tmp_path):
    builder, db = make_builder(tmp_path)
    service = ManagementService(db, ConfigurationRepository(tmp_path / "management"))
    service.ensure_foundations()
    service.create_agent(
        AgentProfile("agent-reviewer-fixture", "Олена", "Проверяет результат", "ACTIVE", "GEMINI_CLI"),
        ["QA_ENGINEER"],
        ["CHAT"],
        reason="test",
    )
    conversation_id = db.create_conversation()

    prompt = builder.build(conversation_id, "hello", agent_key="reviewer-fixture")

    assert "без занудства и давления на пользователя" in prompt
    assert "Не предлагай работу" in prompt


def test_builds_dynamic_employee_context(tmp_path):
    builder, db = make_builder(tmp_path)
    service = ManagementService(db, ConfigurationRepository(tmp_path / "management"))
    service.ensure_foundations()
    service.create_agent(
        AgentProfile(
            agent_id="agent-shushan",
            display_name="Шушан",
            description="Ведет документацию проекта",
            lifecycle_state="ACTIVE",
            provider_id="GEMINI_CLI",
            persona_id="document_control",
        ),
        ["DOCUMENT_CONTROL_OFFICER"],
        ["CHAT"],
        reason="test",
    )
    conversation_id = db.create_conversation()

    prompt = builder.build(conversation_id, "Шушан, ты на месте?", agent_key="shushan")

    assert "Шушан" in prompt
    assert "DOCUMENT_CONTROL_OFFICER" in prompt
    assert "Ведет документацию проекта" in prompt
    assert "Твои права в приложении" in prompt
    assert "CREATE_DOCUMENTS" in prompt
    assert '"agent_id":"agent-shushan"' in prompt


def test_prompt_includes_persistent_thread_snapshot(tmp_path):
    builder, db = make_builder(tmp_path)
    conversation_id = db.create_conversation()

    prompt = builder.build(
        conversation_id,
        "а ограничения?",
        agent_key="roman",
        thread_context_lines=[
            "- conversation_thread_id: conversation-1",
            "- active_addressee_agent_id: agent-shushan",
            "- expected_next_actor: shushan",
        ],
    )

    assert "CONTEXT SNAPSHOT" in prompt
    assert "active_addressee_agent_id: agent-shushan" in prompt
    assert "expected_next_actor: shushan" in prompt


def test_dynamic_employee_gets_relevant_context_without_unrelated_history(tmp_path):
    builder, db = make_builder(tmp_path, limit=2)
    service = ManagementService(db, ConfigurationRepository(tmp_path / "management"))
    service.ensure_foundations()
    service.create_agent(
        AgentProfile(
            agent_id="agent-shushan",
            display_name="Шушан",
            description="Ведет документацию проекта",
            lifecycle_state="ACTIVE",
            provider_id="GEMINI_CLI",
            persona_id="document_control",
        ),
        ["DOCUMENT_CONTROL_OFFICER"],
        ["CHAT"],
        reason="test",
    )
    conversation_id = db.create_conversation()
    db.add_message(conversation_id, "user", "Надо подготовить документацию и проверить ГОСТ.")
    db.add_message(conversation_id, "roman", "unrelated pcb trace width chatter xxyyzz")
    db.add_message(conversation_id, "user", "Еще обсудим музыку позже.")

    prompt = builder.build(
        conversation_id,
        "а ограничения?",
        agent_key="shushan",
        thread_context_lines=["- expected_next_actor: shushan"],
    )

    assert "документацию" in prompt
    assert "ГОСТ" in prompt
    assert "xxyyzz" not in prompt

def test_runtime_selects_only_relevant_verified_skill_packages():
    class DatabaseStub:
        def list_employee_skill_assignments(self, _agent_id):
            return [
                {
                    "skill_status": "VERIFIED", "state": "QUALIFIED", "name": "Проверка BOM",
                    "purpose": "Проверка номиналов и позиций BOM", "skill_id": "SKILL-BOM", "version": "1.0",
                },
                {
                    "skill_status": "PRACTICED", "state": "PRACTICED", "name": "Черновой KiCad",
                    "purpose": "Разводка платы", "skill_id": "SKILL-KICAD", "version": "0.1",
                },
                {
                    "skill_status": "VERIFIED", "state": "QUALIFIED", "name": "Рецепты",
                    "purpose": "Разработка блюд", "skill_id": "SKILL-FOOD", "version": "1.0",
                },
            ]

    builder = PromptBuilder.__new__(PromptBuilder)
    builder.database = DatabaseStub()

    selected = builder._relevant_package_skills("agent-worker", "Проверь номиналы в таблице BOM")

    assert len(selected) == 1
    assert "Проверка BOM" in selected[0]
    assert "Черновой KiCad" not in "\n".join(selected)
    assert "Рецепты" not in "\n".join(selected)
