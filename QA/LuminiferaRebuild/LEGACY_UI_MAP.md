# Luminifera Legacy UI Map

This map documents compatibility UI that remains in the codebase during the
product migration. The default Product Mode is the `LuminiferaShell` path.

| Legacy surface | Purpose | Service/runtime dependencies | Direct DB access | Product replacement | Status |
| --- | --- | --- | --- | --- | --- |
| `MainWindow._build_legacy_ui_reference` | Previous three-column chat/admin layout | chat, director, provider and workspace services | indirect through MainWindow services | `LuminiferaShell` plus Home, Chat, Work, Team and Files panels | KEEP TEMP / Developer fallback |
| `DirectorConsoleDialog` | Organization, employee, role, skill, knowledge and provider administration | management, provider, skill, knowledge, standards and artifact services | service-mediated | Iris and Team/Settings surfaces | KEEP TEMP / explicit admin fallback |
| `SupervisorGuideDialog` | Legacy guide/operator helper | `SupervisorGuideService` | service-mediated | Iris contextual guidance | KEEP TEMP / internal fallback |
| `show_routing_diagnostic` | Routing explanation and internal route details | router and conversation state | service-mediated | hidden in Product Mode; Developer diagnostics only | KEEP TEMP |
| `show_work_context_diagnostic` | Internal work-context details and paths | work context service | service-mediated | Work dashboard and Iris | KEEP TEMP |
| `AuthDialog` / login helpers | Provider login and installation recovery | auth/provider services | service-mediated | Settings > AI connections | KEEP TEMP |
| legacy `chat_widget.py` shell controls | Composer, provider status, routing and task controls | chat/runtime/provider services | service-mediated | Product Chat with automatic routing | REPLACE LATER |

## Product-mode boundary

- `MainWindow._build_ui()` selects `_build_luminifera_ui()` by default.
- The compatibility controls created by `_build_luminifera_ui()` are retained
  for existing runtime callbacks but are not mounted in the Product shell.
- The Product shell exposes only user-facing navigation and Iris; provider
  identifiers, build metadata, filesystem paths and route diagnostics are not
  part of its widget tree.
- Developer diagnostics remain available only through explicit compatibility
  code paths and the `developer_mode` setting.

## Migration rule

Do not remove a legacy surface until its Application Service behavior has a
Product Mode replacement and the engine parity suite has passed. Legacy UI may
be removed later without removing the underlying runtime/service capability.
