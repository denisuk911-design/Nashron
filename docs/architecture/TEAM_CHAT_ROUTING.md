# Team Chat Routing

North Star reference: `docs/product/PRODUCT_NORTH_STAR.md`.

Roman 2050 routes every owner message before any provider is invoked.

Participation modes:
- `DIRECT`: one explicitly addressed employee responds.
- `MULTI_DIRECT`: two or more explicitly addressed employees respond.
- `TEAM_CALL`: all active eligible employees with `CHAT` respond.
- `GENERAL_TEAM_PING`: a presence/group ping such as `Все тут?` responds with short messages from all active eligible employees.
- `REVIEW_REQUEST`: the designated reviewer responds.
- `INFO_ONLY`: information is stored; employees stay silent by default.
- `MANAGEMENT_COMMAND`: configuration-related messages go to management flow or the affected employee.
- `CONTINUATION`: short follow-up goes to the current thread owner.

Default policy: one owner message produces one employee response. Multiple responders are allowed only for explicit multi-direct/team call/general ping, bounded handoff, review request, or critical interruption. A direct mention of an inactive or no-CHAT employee produces no fallback response from Roman.

Ordinary work verbs such as `создай`, `проверь` or `напиши` do not start an autonomous loop by themselves. Autonomous conversation starts only from explicit owner intent such as `цель:`, `пока не выполните` or `говорите между собой`. If an explicit autonomous goal names exactly one employee, the run remains pinned to that employee until a real handoff is produced.

The deterministic router lives in `core/team_routing.py`. `MainWindow` invokes only selected providers and records the decision in `routing_decisions`.
