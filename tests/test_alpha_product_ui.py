from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "apps" / "web" / "static"


def test_alpha_product_shell_has_user_navigation_and_iris_component():
    html = (STATIC / "app.html").read_text(encoding="utf-8")
    for view in ("home", "team", "work", "files", "settings"):
        assert f'data-route="{view}"' in html or f'data-screen="{view}"' in html
    assert 'id="iris-form"' in html
    assert 'id="org-dialog"' in html
    assert '/assets/v3/app.js' in html
    assert '/assets/v3/bridge.js' in html
    assert 'actions.js' not in html
    assert '/assets/v3/config.js' in html
    assert '/assets/v3/styles.css' in html
    assert 'data-view=' not in html
    assert '/assets/alpha.js' not in html
    assert '/assets/premium-rework.js' not in html


def test_landing_is_separate_from_product_app():
    landing = (STATIC / "index.html").read_text(encoding="utf-8")
    assert 'href="/app"' in landing
    assert 'data-view="home"' not in landing


def test_alpha_controller_exposes_product_flows_without_runtime_plumbing():
    script = (STATIC / "v3/bridge.js").read_text(encoding="utf-8")
    for endpoint in ("/api/chat", "/api/goals", "/api/work", "/api/files", "/api/settings"):
        assert endpoint in script
    for method in ("getOrganizations", "getHomeState", "getTeamState", "getWorkState", "getFilesState", "getSettingsState", "createGoal", "startGoal", "submitFeedback"):
        assert f"async {method}" in script
    assert "runtime_id" not in script


def test_alpha_launcher_checks_api_before_serving_web():
    launcher = (ROOT / "scripts" / "run_web.ps1").read_text(encoding="utf-8")
    assert "/api/health" in launcher
    assert "Luminifera API" in launcher
    assert "Start-Process" in launcher
    assert "/app" in launcher


def test_standalone_web_launcher_and_package_spec_exist():
    launcher = (ROOT / "scripts" / "luminifera_web_launcher.py").read_text(encoding="utf-8")
    spec = (ROOT / "LuminiferaWeb.spec").read_text(encoding="utf-8")
    assert "health" in launcher and "webbrowser.open" in launcher
    assert "apps/web/static" in spec and 'name="Luminifera"' in spec
