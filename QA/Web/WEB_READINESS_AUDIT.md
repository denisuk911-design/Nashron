# Luminifera Web Readiness Audit

Date: 2026-08-29

The audit is based on the current Python Core/Application Services and the web boundary in `services/api/app.py`. The browser never opens SQLite and does not own business rules.

| Capability | Status | Boundary / note |
|---|---|---|
| Create and switch organization | READY | `UniversalPlatformService`, scoped header |
| Hire, reassign, archive/delete employee | SERVICE EXTRACTION NEEDED | `ManagementService` exists; web commands need employee forms/actions |
| Create/activate team | SERVICE EXTRACTION NEEDED | `UniversalPlatformService` templates are available |
| Social chat and Iris owner commands | READY | organization conversation + `SupervisorChatApplicationService` |
| Goal create/approve/start/replan/cancel | SERVICE EXTRACTION NEEDED | director boundary exists; dedicated lifecycle routes remain |
| WorkItems and Runtime V3 | SERVICE EXTRACTION NEEDED | `LuminiferaWorkService` read model exists; execution route remains |
| Artifacts/files | READY | `LuminiferaFilesService` and scoped artifact queries |
| Evidence/review/rework/pass | SERVICE EXTRACTION NEEDED | runtime and review services exist, API commands remain |
| Work Receipt | SERVICE EXTRACTION NEEDED | durable runtime data exists, read model to add |
| Provider state/auth | SERVICE EXTRACTION NEEDED | provider registry/health services exist |
| Local Level-1 and Strong routes | SERVICE EXTRACTION NEEDED | runtime adapters remain behind application boundary |
| Skills and Knowledge | SERVICE EXTRACTION NEEDED | services exist; product read/write routes remain |
| Persistence/restart | READY | same `SettingsService` profile and SQLite database |
| Organization isolation | READY | server validates organization and all product reads are scoped |
| Backup/recovery | READY | Web exposes a secret-free profile backup through `ProfileBackupService`; restore remains an explicit local recovery operation |
| Settings/profile/localization | SERVICE EXTRACTION NEEDED | settings service exists; web preference routes remain |

## Phase 01 conclusion

No capability is blocked by PySide for the initial Web path. The first extraction boundary is usable for organizations, scoped chat, Iris commands, home/work/files read models, and artifacts. Remaining work is API surface completion, not a frontend rewrite of domain logic. PySide remains a legacy fallback and test harness.
