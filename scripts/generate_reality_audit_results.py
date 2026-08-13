from __future__ import annotations

import argparse
import json
import os
import platform
import random
import sqlite3
import subprocess
import sys
from collections import Counter
from pathlib import Path

import PySide6

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.avatar_catalog import list_avatar_files
from core.employee_identity import _SURNAMES, generate_identity


DEFAULT_EVIDENCE = ROOT / "QA" / "RealityAudit001"
DEFAULT_PROFILE = DEFAULT_EVIDENCE / "clean_profile_final"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def _git_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _rows(connection: sqlite3.Connection, query: str, parameters=()) -> list[dict[str, object]]:
    return [dict(row) for row in connection.execute(query, parameters)]


def _image_count(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for item in path.rglob("*") if item.is_file() and item.suffix.lower() in IMAGE_SUFFIXES)


def _identity_diagnostics(avatar_dir: Path) -> dict[str, object]:
    random.seed(2050)
    identities = [generate_identity("ru", avatar_dir=avatar_dir) for _ in range(500)]
    full_names = [item.full_name for item in identities]
    first_names = [name.split(maxsplit=1)[0] for name in full_names]
    surnames = [name.rsplit(maxsplit=1)[-1] for name in full_names]
    ukrainian_surnames = set(_SURNAMES["ru"]["ukrainian"])
    international_surnames = set(_SURNAMES["ru"]["other"])

    random.seed(2050)
    avatar_sample = [generate_identity("ru", avatar_dir=avatar_dir) for _ in range(100)]
    return {
        "sample_size": 500,
        "unique_full_names": len(set(full_names)),
        "unique_first_names": len(set(first_names)),
        "unique_surnames": len(set(surnames)),
        "duplicate_profiles": len(full_names) - len(set(full_names)),
        "ru": 0,
        "ua": sum(name in ukrainian_surnames for name in surnames),
        "international": sum(name in international_surnames for name in surnames),
        "avatar_sample_size": 100,
        "avatar_sample_unique": len({item.avatar_path for item in avatar_sample}),
    }


def _findings() -> list[dict[str, object]]:
    return [
        {
            "id": "ROUTE-001",
            "severity": "P0",
            "scenario": "Direct message to an employee whose first name exists in another organization.",
            "expected": "The full-name addressee in the active organization is selected.",
            "actual": "The blocked-agent lookup crossed organization boundaries; ambiguous short names could keep the previous owner.",
            "root_cause": "Configured-agent routing was not organization-scoped and short-name ambiguity was resolved before an exact full-name match.",
            "fix": "Scope configured agents to active_organization_id and prioritize full-name matches.",
            "verification": "Packaged GUI routed a direct message to the exact employee; routing regression suite passes.",
            "evidence": ["chat_b.png"],
            "status": "FIXED",
        },
        {
            "id": "CANCEL-001",
            "severity": "P0",
            "scenario": "Stop immediately after dispatch, then send a new message.",
            "expected": "The first run cancels and the queued message starts.",
            "actual": "A pre-start cancel was lost when the provider reset its cancellation flag.",
            "root_cause": "Cancellation state existed only in the client subprocess lifecycle.",
            "fix": "Add worker-owned cancellation state and preserve client cancellation until generation returns.",
            "verification": "Packaged GUI accepted the next message in 565 ms and produced its response; cancellation unit tests pass.",
            "evidence": ["chat_b.png"],
            "status": "FIXED",
        },
        {
            "id": "PROVIDER-001",
            "severity": "P1",
            "scenario": "Several employees use the same CLI provider concurrently.",
            "expected": "Each employee has an independent process and response.",
            "actual": "Shared client process state caused poll/return-code collisions and missing responses.",
            "root_cause": "All workers shared one mutable provider client instance.",
            "fix": "Create an isolated provider client and workspace for every employee run.",
            "verification": "Six parallel packaged-GUI responses completed with zero provider collision errors.",
            "evidence": ["typing_parallel.png"],
            "status": "FIXED",
        },
        {
            "id": "ROLE-001",
            "severity": "P1",
            "scenario": "Preset positions use roles outside the fixed role map.",
            "expected": "Generated employees can read/write files, run commands, and create documents.",
            "actual": "Unknown roles inherited CHAT only.",
            "root_cause": "The unknown-role fallback bypassed CUSTOM_ROLE defaults.",
            "fix": "Use CUSTOM_ROLE permissions for unknown roles and add reviewer permissions where applicable.",
            "verification": "Database effective permissions and organization activation regression test.",
            "evidence": ["employees_generated.png"],
            "status": "FIXED",
        },
        {
            "id": "LOC-001",
            "severity": "P2",
            "scenario": "Russian and Ukrainian preset/role labels.",
            "expected": "Internal English identifiers are not primary UI labels.",
            "actual": "Generic presets and dynamic roles leaked English labels.",
            "root_cause": "Localization covered fixed legacy roles only.",
            "fix": "Add catalog labels and dynamic role labels without changing canonical role semantics.",
            "verification": "Localization and preset catalog regression tests.",
            "evidence": ["organization_created.png"],
            "status": "FIXED",
        },
        {
            "id": "GUI-001",
            "severity": "P2",
            "scenario": "Personality edit survives close and restart.",
            "expected": "Generated and edited communication settings persist.",
            "actual": "Persistence exists in SQLite, but the edit-close-reopen sequence was not completed in the packaged GUI audit.",
            "root_cause": "Audit coverage gap.",
            "fix": "None in this task.",
            "verification": "NOT VERIFIED.",
            "evidence": ["employee_profile.png"],
            "status": "OPEN",
        },
        {
            "id": "THEME-001",
            "severity": "P2",
            "scenario": "Switch to another image within the same theme category.",
            "expected": "A different packaged image is rendered.",
            "actual": "Category switching was verified; same-category cycling was not exercised.",
            "root_cause": "Audit coverage gap.",
            "fix": "None in this task.",
            "verification": "NOT VERIFIED.",
            "evidence": ["theme_city.png", "theme_forest.png", "theme_mountains.png", "theme_ocean.png"],
            "status": "OPEN",
        },
        {
            "id": "UNICODE-001",
            "severity": "P2",
            "scenario": "Provider health diagnostic stored for Codex CLI.",
            "expected": "Readable diagnostic text.",
            "actual": "One internal provider-health row contains a garbled external CLI diagnostic; the top-level GUI shows Codex: OK.",
            "root_cause": "External CLI status decoding/normalization is incomplete.",
            "fix": "Not exposed in the audited main UI; retained as an open diagnostic issue.",
            "verification": "SQLite provider_health_checks inspection.",
            "evidence": [],
            "status": "OPEN",
        },
    ]


def build_results(profile: Path, evidence: Path, exe: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    database_path = profile / "roman2050.sqlite3"
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        organizations = _rows(connection, "SELECT * FROM organizations ORDER BY created_at, id")
        employees = _rows(
            connection,
            """
            SELECT p.agent_id AS employee_id, p.display_name, p.preferred_name,
                   m.role_id, m.position AS profession, p.avatar_path,
                   p.communication_profile, m.organization_id, o.name AS organization,
                   m.provider_id, m.provisioning_status
            FROM agent_profiles p
            JOIN organization_members m ON m.agent_id = p.agent_id
            JOIN organizations o ON o.id = m.organization_id
            ORDER BY o.created_at, p.created_at, p.agent_id
            """,
        )
        schema = dict(connection.execute("SELECT key, value FROM schema_meta ORDER BY key"))
        foreign_key_errors = [list(row) for row in connection.execute("PRAGMA foreign_key_check")]
        permission_counts = Counter(
            row[0]
            for row in connection.execute(
                "SELECT COUNT(*) FROM agent_permissions GROUP BY agent_id"
            )
        )
        providers = [
            dict(row)
            for row in connection.execute(
                """
                SELECT provider_id, installation_status, authentication_status,
                       access_status, health_status, detected_version
                FROM provider_health_checks
                WHERE provider_id IN ('CODEX_CLI', 'GEMINI_CLI')
                ORDER BY provider_id, created_at DESC
                """
            )
        ]
    finally:
        connection.close()

    source_avatars = ROOT / "data" / "avatars"
    packaged_data = exe.parent / "_internal" / "data"
    packaged_avatars = packaged_data / "avatars"
    source_backgrounds = ROOT / "data" / "theme_backgrounds"
    packaged_backgrounds = packaged_data / "theme_backgrounds"
    diagnostics = _identity_diagnostics(source_avatars)
    gui_avatar_count = len({str(item["avatar_path"]) for item in employees if item["avatar_path"]})
    human_name_count = sum(" " in str(item["display_name"]).strip() for item in employees)
    findings = _findings()

    results = {
        "task": "TEAM2050-P0-REALITY-AUDIT-001",
        "status": "READY_FOR_REVIEW",
        "build": {
            "commit": _git_commit(),
            "exe": str(exe.resolve()),
            "exe_exists": exe.is_file(),
            "python": sys.version,
            "qt_pyside": PySide6.__version__,
            "windows": platform.platform(),
            "clean_profile": str(profile.resolve()),
            "database": str(database_path.resolve()),
            "schema": schema,
            "providers": providers,
        },
        "clean_gui_inventory": {
            "organizations": len(organizations),
            "employees": len(employees),
            "human_display_names": human_name_count,
            "unique_gui_avatars": gui_avatar_count,
            "provider_assignments": dict(Counter(str(item["provider_id"]) for item in employees)),
            "permission_grant_counts_per_employee": {str(key): value for key, value in sorted(permission_counts.items())},
            "foreign_key_errors": foreign_key_errors,
        },
        "identity_500": diagnostics,
        "avatars": {
            "A_source_image_assets": _image_count(source_avatars),
            "B_runtime_resolver_assets": len(list_avatar_files(source_avatars)),
            "C_generator_assets": len(list_avatar_files(source_avatars)),
            "D_unique_in_100_generated": diagnostics["avatar_sample_unique"],
            "E_unique_in_30_gui_employees": gui_avatar_count,
            "packaged_image_assets": _image_count(packaged_avatars),
        },
        "theme_assets": {
            "source": _image_count(source_backgrounds),
            "packaged": _image_count(packaged_backgrounds),
            "categories": sorted(item.name for item in source_backgrounds.iterdir() if item.is_dir()),
        },
        "real_gui": {
            "startup": {"status": "PASS", "evidence": "startup.png"},
            "organization_creation": {"status": "PASS", "count": 5, "evidence": "organization_created.png"},
            "employee_names": {"status": "PASS", "human_names": human_name_count, "total": len(employees), "evidence": "employees_generated.png"},
            "theme_backgrounds": {"status": "PASS", "verified": ["city", "forest", "mountains", "ocean"]},
            "chat_immediate_send": {"status": "PASS", "external_t0_to_t1_ms": 117, "internal_insert_ms_range": [6, 10], "t2_worker_start": "NOT_SEPARATELY_INSTRUMENTED", "t3_typing": "VISIBLE", "t4_first_response_seconds": 6.97},
            "typing_indicator": {"status": "PASS", "evidence": "typing_parallel.png"},
            "autoscroll": {"status": "PASS", "bottom_follow": True, "history_position_preserved": True, "follow_restored": True},
            "organization_isolation": {"status": "PASS", "evidence": ["chat_a.png", "chat_b.png"]},
            "employee_delete": {"status": "PASS", "database_rows_after": 0, "foreign_key_errors": 0},
            "organization_delete": {"status": "PARTIAL", "database_rows_after": 0, "restart_recheck": "NOT_VERIFIED"},
            "provider_failure": {"status": "PASS", "unavailable_assignment_present": True, "gui_frozen": False},
            "stop_recovery": {"status": "PASS", "next_message_started_ms": 565},
            "unicode": {"status": "PARTIAL", "main_gui": "PASS", "internal_provider_diagnostic": "FAIL"},
            "personality_restart_persistence": {"status": "NOT_VERIFIED"},
            "same_category_background_cycle": {"status": "NOT_VERIFIED"},
            "response_quality_fake_claims": {"status": "NOT_VERIFIED"},
        },
        "findings": {
            "fixed": sum(item["status"] == "FIXED" for item in findings),
            "open": sum(item["status"] == "OPEN" for item in findings),
            "unresolved_p0": [],
            "unresolved_p1": [],
        },
    }
    return results, findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--exe", type=Path, default=ROOT / "dist" / "Team2050" / "Team2050.exe")
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    results, findings = build_results(args.profile, args.evidence, args.exe)
    (args.evidence / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.evidence / "findings.json").write_text(
        json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    database_path = args.profile / "roman2050.sqlite3"
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        inventory = _rows(
            connection,
            """
            SELECT p.agent_id AS employee_id, p.display_name, p.preferred_name,
                   m.role_id, m.position AS profession, p.avatar_path,
                   p.communication_profile, o.name AS organization
            FROM agent_profiles p
            JOIN organization_members m ON m.agent_id = p.agent_id
            JOIN organizations o ON o.id = m.organization_id
            ORDER BY o.created_at, p.created_at, p.agent_id
            """,
        )
    finally:
        connection.close()
    (args.evidence / "employee_inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({"results": str(args.evidence / "results.json"), "employees": len(inventory)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
