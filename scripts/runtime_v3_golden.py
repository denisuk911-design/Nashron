from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.agent_directory import ChatAgent
from core.runtime_v3_service import RuntimeV3GoalService


GOLDEN_GOAL = "Подготовьте техническую спецификацию преобразователя 24 В -> 12 В, 5 А и подберите подходящий контроллер."


def main() -> int:
    service = RuntimeV3GoalService(PROJECT_ROOT / ".tmp_runtime_v3_golden")
    agents = [
        ChatAgent("engineer", "agent-engineer", "Engineer", "LOCAL", ["DESIGN_ENGINEER"], "engineer", "", None),
        ChatAgent("researcher", "agent-researcher", "Researcher", "LOCAL", ["RESEARCHER"], "researcher", "", None),
        ChatAgent("reviewer", "agent-reviewer", "Reviewer", "LOCAL", ["QA_ENGINEER"], "reviewer", "", None),
    ]
    result = service.run_goal("golden-org", GOLDEN_GOAL, agents)
    payload = {
        "ok": result.ok,
        "summary": result.summary,
        "goal_count": len(result.state.goals),
        "work_items": len(result.state.work_items),
        "actions": len(result.state.actions),
        "observations": len(result.state.observations),
        "artifacts": len(result.state.artifacts),
        "evidence": len(result.state.evidence),
        "findings": len(result.state.findings),
        "handoffs": len(result.state.handoffs),
        "workspace": str(result.workspace_root),
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if result.ok and payload["artifacts"] >= 3 and payload["handoffs"] >= 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())
