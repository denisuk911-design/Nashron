# Team Chat Routing

North Star reference: `docs/product/PRODUCT_NORTH_STAR.md`.

Roman 2050 routes every owner message before any provider is invoked.

Participation modes:
- `DIRECT`: one explicitly addressed employee responds.
- `TEAM_DISCUSSION`: only the selected team subset responds.
- `REVIEW_REQUEST`: the designated reviewer responds.
- `BROADCAST`: information is stored; employees stay silent by default.
- `MANAGEMENT_COMMAND`: configuration-related messages go to management flow or the affected employee.
- `CONTINUATION`: short follow-up goes to the current thread owner.

Default policy: one owner message produces one employee response. Multiple responders are allowed only for explicit team discussion, handoff, review request, or critical interruption.

Ordinary work verbs such as `создай`, `проверь` or `напиши` do not start an autonomous loop by themselves. Autonomous conversation starts only from explicit owner intent such as `цель:`, `пока не выполните` or `говорите между собой`. If an explicit autonomous goal names exactly one employee, the run remains pinned to that employee until a real handoff is produced.

The deterministic router lives in `core/team_routing.py`. `MainWindow` invokes only selected providers and records the decision in `routing_decisions`.
