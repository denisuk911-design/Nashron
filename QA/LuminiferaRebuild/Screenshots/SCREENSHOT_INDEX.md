# Luminifera Screenshot Index

All entries below are screenshots from the packaged `dist/Team2050/Team2050.exe`.
The `accept_*_latest` set was captured after the latest rebuild on isolated
profiles; each corresponding JSON report has `checks_passed=true`.

| Screen | Scenario | Reference | Known deviation |
| --- | --- | --- | --- |
| `accept_onboarding_latest.png` | Clean first run | `01_LUMINIFERA_ONBOARDING_REFERENCE.png` | Manual visual review pending |
| `accept_home_latest.png` | Empty workspace entry | `02_LUMINIFERA_MAIN_WORKSPACE_REFERENCE.png` | Manual visual review pending |
| `accept_iris_latest.png` | Iris owner surface | `03_IRIS_SUPERVISOR_REFERENCE.png` | Full reference composition remains simplified |
| `accept_team_latest.png` | Team proposal flow | `04_LUMINIFERA_TEAM_SETTINGS_REFERENCE.png` | Generated populated cards need manual review |
| `accept_team_roster_latest.png` | Team roster | `04_LUMINIFERA_TEAM_SETTINGS_REFERENCE.png` | Empty-state recovery shown in clean profile |
| `accept_work_latest.png` | Work/goal empty state | `02_LUMINIFERA_MAIN_WORKSPACE_REFERENCE.png` | Populated goal requires manual review |
| `accept_chat_latest.png` | Product chat | `02_LUMINIFERA_MAIN_WORKSPACE_REFERENCE.png` | Conversation data is isolated from clean profile |
| `accept_files_latest.png` | Files/artifacts | `02_LUMINIFERA_MAIN_WORKSPACE_REFERENCE.png` | Empty-state recovery shown in clean profile |
| `accept_settings_latest.png` | Settings | `04_LUMINIFERA_TEAM_SETTINGS_REFERENCE.png` | Provider editing remains in compatibility flow |
| `accept_profile_latest.png` | Owner profile | `01_LUMINIFERA_ONBOARDING_REFERENCE.png` | Manual visual review pending |
| `state_catalog_recheck.png` | Product Work state | `02_LUMINIFERA_MAIN_WORKSPACE_REFERENCE.png` | Catalog states are also covered by unit tests |
| `visual_polish_recheck.png` | Focus/progress styling | `02_LUMINIFERA_MAIN_WORKSPACE_REFERENCE.png` | Manual interaction review pending |
| `responsive_1366x768.png` | Responsive Home | `02_LUMINIFERA_MAIN_WORKSPACE_REFERENCE.png` | Manual wide-screen review pending |
| `responsive_1920x1080.png` | Responsive Home | `02_LUMINIFERA_MAIN_WORKSPACE_REFERENCE.png` | Manual wide-screen review pending |
| `responsive_2560x1440.png` | Responsive Home | `02_LUMINIFERA_MAIN_WORKSPACE_REFERENCE.png` | Manual wide-screen review pending |

The reference images are preserved in `Инструкции/`; this index records actual
runtime output and does not claim owner visual approval.
