import json
import sqlite3
import zipfile

from core.feedback_service import FeedbackService


def test_feedback_report_contains_build_and_no_diagnostics_without_consent(tmp_path):
    profile = tmp_path / "profile"
    profile.mkdir()
    output = tmp_path / "feedback.zip"

    FeedbackService(tmp_path / "install").create_report(profile, output, "Кнопка не отвечает")

    with zipfile.ZipFile(output) as archive:
        assert archive.namelist() == ["feedback.json"]
        report = json.loads(archive.read("feedback.json"))
    assert report["description"] == "Кнопка не отвечает"
    assert report["diagnostics_attached"] is False
    assert report["build"]["version"]


def test_feedback_report_attaches_sanitized_support_only_after_consent(tmp_path):
    profile = tmp_path / "profile"
    profile.mkdir()
    connection = sqlite3.connect(profile / "team2050.sqlite3")
    connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY)")
    connection.commit()
    connection.close()
    (profile / "secret.txt").write_text("AQ.secret-token", encoding="utf-8")
    install = tmp_path / "install"
    install.mkdir()
    (install / "Team2050.exe").write_bytes(b"fake")
    output = tmp_path / "feedback.zip"

    FeedbackService(install).create_report(profile, output, "Ошибка запуска", attach_diagnostics=True)

    with zipfile.ZipFile(output) as archive:
        assert set(archive.namelist()) == {"feedback.json", "support-report.json"}
        report = json.loads(archive.read("support-report.json"))
        payload = archive.read("support-report.json").decode("utf-8")
    assert report["secrets_included"] is False
    assert "AQ.secret-token" not in payload
    assert "not exported" not in payload
