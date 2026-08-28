from core.database import Database
from core.profession_workspace_service import ProfessionWorkspaceService
from core.skill_marketplace_service import SkillMarketplaceService, SkillPackManifest
from core.skill_package_service import SkillPackageService


def test_profession_workspaces_are_scoped_to_role_tools_skills_and_dod(tmp_path):
    db = Database(tmp_path / "team.sqlite3"); db.initialize()
    with db.connect() as conn:
        conn.execute("INSERT INTO organizations (id,name,purpose,status) VALUES ('org-a','A','', 'ACTIVE')")
        conn.execute("INSERT INTO organizations (id,name,purpose,status) VALUES ('org-b','B','', 'ACTIVE')")
        for agent in ("dev", "eng", "res"):
            conn.execute("INSERT INTO agent_profiles (agent_id,display_name,description,lifecycle_state,provider_id,schema_version) VALUES (?, ?, '', 'ACTIVE', 'CODEX_CLI', '1.0')", (agent, agent))
    developer = db.create_profession({"name":"Developer", "recommended_tools":["terminal.run","workspace.write"], "typical_results":["tests pass"]})
    engineer = db.create_profession({"name":"Engineer", "recommended_tools":["workspace.write","artifact.review"], "typical_results":["design reviewed"]})
    researcher = db.create_profession({"name":"Researcher", "recommended_tools":["workspace.read","browser.call"], "typical_results":["sources recorded"]})
    with db.connect() as conn:
        for agent, profession in (("dev", developer), ("eng", engineer), ("res", researcher)):
            conn.execute("INSERT INTO organization_members (id,organization_id,agent_id,profession_id,status) VALUES (?, 'org-a', ?, ?, 'ACTIVE')", (f'm-{agent}', agent, profession))
    service = ProfessionWorkspaceService(db, tmp_path / "workspace")
    assert service.for_employee("org-a", "dev").tools == ("terminal.run", "workspace.write")
    assert service.for_employee("org-a", "eng").definition_of_done == ("design reviewed",)
    assert service.for_employee("org-a", "res").tools == ("workspace.read", "browser.call")
    assert service.for_employee("org-a", "dev").root != service.for_employee("org-a", "eng").root
    try: service.for_employee("org-b", "dev")
    except ValueError: pass
    else: raise AssertionError("organization isolation bypassed")


def test_active_qualified_skill_extends_only_its_employee_workspace_after_restart(tmp_path):
    db = Database(tmp_path / "team.sqlite3"); db.initialize()
    with db.connect() as conn:
        conn.execute("INSERT INTO organizations (id,name,purpose,status) VALUES ('org-a','A','', 'ACTIVE')")
        conn.execute("INSERT INTO agent_profiles (agent_id,display_name,description,lifecycle_state,provider_id,schema_version) VALUES ('eng','eng','', 'ACTIVE', 'CODEX_CLI', '1.0')")
    profession = db.create_profession({"name":"Engineer", "recommended_tools":["workspace.write"], "typical_results":["design"]})
    with db.connect() as conn:
        conn.execute("INSERT INTO organization_members (id,organization_id,agent_id,profession_id,status) VALUES ('m','org-a','eng',?, 'ACTIVE')", (profession,))
    packages=SkillPackageService(db); market=SkillMarketplaceService(packages)
    pack=market.install("org-a", SkillPackManifest("ERC","purpose","procedure",("ref",),("check",),("workspace.read",),("test",),("accept",),("example",),("failure",)))
    packages.update_status(pack,"VERIFIED",actor="qa",reason="evidence:review_run:R",organization_id="org-a")
    packages.assign_to_employee("eng",pack,state="QUALIFIED",actor="qa",reason="review_run:R")
    market.activate(pack,"org-a")
    restored=ProfessionWorkspaceService(Database(db.path),tmp_path / "workspace").for_employee("org-a","eng")
    assert restored.skills == ("ERC",) and "accept" in restored.definition_of_done
