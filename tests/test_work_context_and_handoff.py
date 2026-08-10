from core.artifact_service import ArtifactService
from core.database import Database
from core.work_context_service import (
    ArtifactReference,
    ArtifactReferentResolver,
    IntentResolver,
    IntentType,
    OutputValidator,
    WorkContextService,
)


def test_bom_flow_keeps_the_real_artifact_and_creates_contract(tmp_path):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    conversation_id = database.create_conversation("Отдел важных дел")
    database.ensure_project("project-default", "Team")
    task_id = database.create_task("project-default", "BOM", None, "1.0")
    work = WorkContextService(database, conversation_id, f"conversation-{conversation_id}")
    intents = IntentResolver()
    resolver = ArtifactReferentResolver(database)
    names = {"roman": ["Роман"], "shushan": ["Шушанна", "Шуша"]}

    create = intents.resolve("Давай BOM", names)
    assert create.intent == IntentType.CREATE
    work.apply_command(text="Давай BOM", intent=create, reference=resolver.resolve("Давай BOM", None), selected_agent_keys=["roman"], task_id=task_id)

    artifacts = ArtifactService(database, tmp_path)
    bom_id = artifacts.register_chat_artifact(
        content="| Ref | Value |\n| AP63205WU-7 | 5V |",
        title="DC_DC_5V_Buck BOM",
        artifact_type="BOM",
        task_id=task_id,
        run_id="RUN-ROMAN",
        source_agent_id="roman",
    )
    context = work.get()
    assert context is not None
    work.record_result(artifact_ids=[bom_id], action="roman: CREATE", validation=type("V", (), {"accepted": True, "code": "OK"})())

    format_intent = intents.resolve("Шушанна, оформляй", names)
    reference = resolver.resolve("Шушанна, оформляй", work.get())
    assert format_intent.intent == IntentType.FORMAT
    assert reference.primary_artifact_id == bom_id
    assert reference.artifact_type == "BOM"

    context = work.apply_command(
        text="Шушанна, оформляй",
        intent=format_intent,
        reference=reference,
        selected_agent_keys=["shushan"],
    )
    assert context.task_id == task_id
    assert context.primary_artifact_id == bom_id
    assert context.expected_output_type == "BOM_DOCUMENT"
    assert database.list_work_handoffs(conversation_id)

    contract = work.create_contract(
        context=context,
        intent=format_intent,
        user_instruction="Шушанна, оформляй",
        agent_id="agent-shushan",
        role="DOCUMENT_CONTROL_OFFICER",
        run_id="RUN-SHUSHAN",
        allowed_tools=["WRITE_WORKSPACE"],
    )
    assert bom_id in contract.input_artifact_ids
    assert "memo" in " ".join(contract.forbidden_substitutions)
    assert database.get_execution_contract(contract.contract_id) is not None


def test_explicit_bom_never_falls_back_to_stale_memo(tmp_path):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    conversation_id = database.create_conversation("Отдел")
    work = WorkContextService(database, conversation_id, f"conversation-{conversation_id}")
    database.ensure_project("project-default", "Team")
    task_id = database.create_task("project-default", "old", None, "1.0")
    work.apply_command(
        text="Создай memo",
        intent=IntentResolver().resolve("Создай memo"),
        reference=ArtifactReferentResolver(database).resolve("Создай memo", None),
        selected_agent_keys=["shushan"],
        task_id=task_id,
    )
    artifacts = ArtifactService(database, tmp_path)
    memo_id = artifacts.register_chat_artifact(
        content="служебная записка",
        title="memo_001",
        artifact_type="MD",
        task_id=task_id,
        run_id="RUN-1",
        source_agent_id="shushan",
    )
    current = work.get()
    assert current is not None
    work.record_result(artifact_ids=[memo_id], action="memo", validation=type("V", (), {"accepted": True, "code": "OK"})())
    reference = ArtifactReferentResolver(database).resolve("Шушанна, бери BOM у Романа и оформляй", work.get())
    assert reference.primary_artifact_id is None


def test_output_validator_rejects_memo_for_bom_document(tmp_path):
    database = Database(tmp_path / "team.sqlite3")
    database.initialize()
    conversation_id = database.create_conversation("Отдел")
    work = WorkContextService(database, conversation_id, f"conversation-{conversation_id}")
    intent = IntentResolver().resolve("Шушанна, оформляй")
    context = work.apply_command(
        text="Шушанна, оформляй",
        intent=intent,
        reference=ArtifactReference(
            artifact_ids=("ART-1",),
            primary_artifact_id="ART-1",
            artifact_type="BOM",
            source_agent_id="roman",
            reason="TEST",
        ),
        selected_agent_keys=["shushan"],
    )
    contract = work.create_contract(
        context=context,
        intent=intent,
        user_instruction="оформляй",
        agent_id="agent-shushan",
        role="DOCUMENT_CONTROL_OFFICER",
        run_id="RUN-1",
        allowed_tools=[],
    )
    result = OutputValidator().validate(contract, "Создала memo_001.md", [])
    assert not result.accepted
    assert result.code == "OUTPUT_TYPE_MISMATCH"
