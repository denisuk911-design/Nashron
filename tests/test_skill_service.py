from core.skill_service import SkillService


def test_learns_and_lists_agent_skill(tmp_path):
    service = SkillService(tmp_path / "agent_skills.json")
    service.learn_from_exchange("petr", "сделай отчет по файлам", "Сначала проверяю структуру, потом считаю итоги.")

    skills = service.list_for_prompt("petr")

    assert len(skills) == 1
    assert "сделай отчет" in skills[0]
    assert "Сначала проверяю" in skills[0]


def test_improves_existing_skill(tmp_path):
    service = SkillService(tmp_path / "agent_skills.json")
    service.learn_from_exchange("roman", "проверь текст", "Смотрю повторы.")
    service.learn_from_exchange("roman", "проверь текст", "Смотрю повторы и тон.")

    data = service.load()

    assert len(data["roman"]) == 1
    assert data["roman"][0]["uses"] == 2
    assert "тон" in data["roman"][0]["note"]


def test_improves_skill_from_context(tmp_path):
    service = SkillService(tmp_path / "agent_skills.json")

    service.improve_from_context("petr", "создать skill для KiCad", "Проверяю структуру, источники и сухость инструкций.")

    skills = service.list_for_prompt("petr")
    assert len(skills) == 1
    assert "skill" in skills[0]
    assert "Проверяю структуру" in skills[0]


def test_load_preserves_dynamic_employee_skills(tmp_path):
    service = SkillService(tmp_path / "agent_skills.json")

    service.learn_from_exchange("employee-shushan", "create docs standard", "Checks docs and writes concise rules.")

    data = service.load()
    assert "employee-shushan" in data
    assert service.list_for_prompt("employee-shushan")
