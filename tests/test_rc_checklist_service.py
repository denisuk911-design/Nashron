from __future__ import annotations

import json

from core.rc_checklist_service import RcChecklistService


def test_rc_checklist_runs_real_isolated_checks_and_keeps_manual_gate_pending(tmp_path):
    service = RcChecklistService(tmp_path / "profile")

    checks = service.run()
    payload = json.loads(service.report_path.read_text(encoding="utf-8"))

    assert len(checks) == 8
    assert all(item.automated == "PASS" for item in checks)
    assert payload["automated_pass"] is True
    assert payload["manual_acceptance"] == "PENDING"
    assert payload["manual_acceptance_is_required"] is True
    assert all(item["manual_status"] == "PENDING" for item in payload["checks"])
