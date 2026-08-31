# Luminifera UI Rebuild Execution Log

## STEP 01 - Application Shell / Navigation

STEP: 01
STATUS: TECHNICAL PASS; VISUAL REVIEW PENDING OWNER
TECHNICAL_TESTS: 30 passed (`test_luminifera_shell`, `test_startup_bootstrap`, `test_main_window_helpers`, `test_theme_manager`)
PACKAGED_TEST: PASS (`checks_passed=true`, clean isolated profile, demo sandbox completed)
ENGINE_PARITY: Startup, organization selector, chat surface, social/work mode callbacks, Iris callback, settings/profile callbacks and demo sandbox remain connected to existing services.
VISUAL_SCREENSHOT: `QA/LuminiferaRebuild/Screenshots/01_application_shell_actual.png`
KNOWN_GAPS: STEP 01 changes only the application chrome. The central first-run/onboarding surface remains legacy until STEP 02. The bundled executable keeps its internal `Team2050.exe` filename during migration.
FILES_CHANGED: `core/branding.py`; `gui/main_window.py`; `gui/theme/theme_manager.py`; `ui_luminifera/`; `tests/test_luminifera_shell.py`; `QA/LuminiferaRebuild/`

## STEP 02 - Onboarding / First Run

STEP: 02
STATUS: PASS; visual review retained for final owner review
TECHNICAL_TESTS: 31 passed (`test_startup_bootstrap`, `test_luminifera_shell`, `test_main_window_helpers`, `test_theme_manager`)
PACKAGED_TEST: PASS (`checks_passed=true`, clean isolated profile, `Luminifera` window title)
ENGINE_PARITY: First-team creation, demo sandbox, language persistence and owner avatar persistence remain connected to their existing services.
VISUAL_SCREENSHOT: `QA/LuminiferaRebuild/Screenshots/01_onboarding.png`
KNOWN_GAPS: Final space imagery, window chrome and owner profile editor are later dedicated steps.
FILES_CHANGED: `gui/main_window.py`; `gui/theme/theme_manager.py`; `ui_luminifera/onboarding/`; `ui_luminifera/app_shell/shell.py`; `tests/test_startup_bootstrap.py`; `QA/LuminiferaRebuild/`

## STEP 03 - Home / Workspace Entry

STEP: 03
STATUS: PASS; visual review retained for final owner review
TECHNICAL_TESTS: 32 passed (`test_startup_bootstrap`, `test_luminifera_shell`, `test_main_window_helpers`, `test_theme_manager`)
PACKAGED_TEST: PASS; `dist/Team2050/Team2050.exe` launched in an isolated preview profile and generated `02_home_empty.json` with `checks_passed=true`
ENGINE_PARITY: Home reads organization, roster, task and artifact state through `LuminiferaHomeService`; runtime provider and orchestration behavior is unchanged.
VISUAL_SCREENSHOT: `QA/LuminiferaRebuild/Screenshots/02_home_empty.png`
KNOWN_GAPS: Active-organization Home state is covered by source tests; the full visual scenario will be captured during final acceptance.
FILES_CHANGED: `core/luminifera_home_service.py`; `ui_luminifera/home/`; `gui/main_window.py`; `gui/theme/theme_manager.py`; `app.py`; `tests/test_startup_bootstrap.py`

## STEP 04 - Iris Owner Surface

STEP: 04
STATUS: PASS; visual review retained for final owner review
TECHNICAL_TESTS: 40 passed (39 existing targeted tests plus `test_iris_dialog`)
PACKAGED_TEST: PASS; `dist/Team2050/Team2050.exe` generated `03_iris.json` with `checks_passed=true`
ENGINE_PARITY: Iris remains backed by `SupervisorChatApplicationService`, management, organization, settings, Goal and provider callbacks; dangerous actions retain confirmation.
VISUAL_SCREENSHOT: `QA/LuminiferaRebuild/Screenshots/03_iris.png`
KNOWN_GAPS: Full multi-panel Iris reference composition and team-builder cards are covered by later product steps.
FILES_CHANGED: `gui/supervisor_chat_dialog.py`; `gui/main_window.py`; `app.py`; `tests/test_iris_dialog.py`

## STEP 05 - Team Builder / Proposal

STEP: 05
STATUS: PASS; visual review retained for final owner review
TECHNICAL_TESTS: 17 focused tests passed (`test_luminifera_team_builder`, startup, Iris and application-service contracts)
PACKAGED_TEST: PASS; packaged team proposal preview generated `04_team_builder.json` with `checks_passed=true`
ENGINE_PARITY: Proposal confirmation invokes `UniversalPlatformService.build_professional_team`; team selection remains deterministic and domain-aware.
VISUAL_SCREENSHOT: `QA/LuminiferaRebuild/Screenshots/04_team_builder.png`
KNOWN_GAPS: Rich employee cards with avatar, status and skill details are a later refinement of the team surface; current proposal exposes human-readable roles and responsibilities.
FILES_CHANGED: `ui_luminifera/team/`; `gui/main_window.py`; `gui/theme/theme_manager.py`; `core/universal_platform_service.py`; `app.py`; `tests/test_luminifera_team_builder.py`

## STEP 06 - Work / Goals

STEP: 06
STATUS: PASS; visual review retained for final owner review
TECHNICAL_TESTS: 13 focused UI tests passed (startup, team builder, Iris and shell contracts)
PACKAGED_TEST: PASS; packaged Work preview generated `05_work.json` with `checks_passed=true`
ENGINE_PARITY: Work state is read through `LuminiferaWorkService` from existing organizations, tasks, artifacts and findings; task execution remains unchanged.
VISUAL_SCREENSHOT: `QA/LuminiferaRebuild/Screenshots/05_work.png`
KNOWN_GAPS: Goal detail, work receipt and populated active-goal screenshot are covered by later acceptance and polish steps.
FILES_CHANGED: `core/luminifera_work_service.py`; `ui_luminifera/work/`; `gui/main_window.py`; `gui/theme/theme_manager.py`; `app.py`

## STEP 07 - Product Chat

STEP: 07
STATUS: PASS; visual review retained for final owner review
TECHNICAL_TESTS: 16 focused chat/bootstrap tests passed
PACKAGED_TEST: PASS; packaged chat preview generated `06_chat.json` with `checks_passed=true`
ENGINE_PARITY: Existing multi-message selection, smooth wheel scrolling, attachment flow, automatic routing and stop handling remain available; persistent routing selectors are hidden in Product Mode.
VISUAL_SCREENSHOT: `QA/LuminiferaRebuild/Screenshots/06_chat.png`
KNOWN_GAPS: Populated team conversation and attachment gallery are verified in later acceptance screenshots.
FILES_CHANGED: `gui/chat_widget.py`; `gui/main_window.py`; `app.py`

## STEP 08 - Files / Artifacts

STEP: 08
STATUS: PASS; visual review retained for final owner review
TECHNICAL_TESTS: 17 focused tests passed, including `test_luminifera_files`
PACKAGED_TEST: PASS; packaged Files preview generated `07_files.json` with `checks_passed=true`; actual screenshot reviewed
ENGINE_PARITY: Files are read through `LuminiferaFilesService` from persisted organization artifacts; opening the workspace remains connected to the existing workspace service.
VISUAL_SCREENSHOT: `QA/LuminiferaRebuild/Screenshots/07_files.png`
KNOWN_GAPS: Artifact detail, preview and export actions remain bounded to the later artifact and final-acceptance steps; no absolute workspace paths are exposed in the product list.
FILES_CHANGED: `core/luminifera_files_service.py`; `ui_luminifera/files/`; `ui_luminifera/app_shell/shell.py`; `gui/main_window.py`; `app.py`; `tests/test_luminifera_files.py`

## STEP 09 - Settings / Providers

STEP: 09
STATUS: PASS; visual review retained for final owner review
TECHNICAL_TESTS: 12 focused settings/files/team/Iris/bootstrap tests passed
PACKAGED_TEST: PASS; packaged settings preview generated `08_settings.json` with `checks_passed=true`; actual screenshot reviewed
ENGINE_PARITY: Theme, language, sound, response mode, local-tools policy and workspace values continue through the existing MainWindow settings application path; provider health remains owned by the existing provider services.
VISUAL_SCREENSHOT: `QA/LuminiferaRebuild/Screenshots/08_settings.png`
KNOWN_GAPS: Provider credential editing and advanced diagnostics remain intentionally behind the compact product settings surface; provider health is still checked by the runtime rather than fabricated by the UI.
FILES_CHANGED: `ui_luminifera/settings/`; `gui/main_window.py`; `app.py`; `tests/test_luminifera_settings.py`

## STEP 10 - Profile / Owner Avatar

STEP: 10
STATUS: PASS; visual review retained for final owner review
TECHNICAL_TESTS: 13 focused profile/settings/files/bootstrap tests passed
PACKAGED_TEST: PASS; source and packaged preview path generated `09_profile.json` with `checks_passed=true`; actual profile screenshot reviewed
ENGINE_PARITY: Owner identity is persisted through the existing settings service and remains separate from employee avatar data; profile changes update the product shell immediately.
VISUAL_SCREENSHOT: `QA/LuminiferaRebuild/Screenshots/09_profile.png`
KNOWN_GAPS: A richer preference summary can be added during final polish; upload, choose, remove and persistence are implemented.
FILES_CHANGED: `ui_luminifera/profile/`; `gui/main_window.py`; `app.py`; `tests/test_luminifera_profile.py`

## STEP 11 - Product States

STEP: 11
STATUS: PARTIAL; goal-state copy and the critical response-start failure path are now localized and readable, while the full unified error-copy catalog still requires a dedicated polish pass.
TECHNICAL_TESTS: 45 focused state/shell/files/settings/profile/runtime-v3 tests passed
PACKAGED_TEST: PASS; packaged Work state and final Home previews generated `10_states.json` and `final4_home.json` with `checks_passed=true`; actual screenshots reviewed
VISUAL_SCREENSHOT: `QA/LuminiferaRebuild/Screenshots/10_states.png`
KNOWN_GAPS: Some legacy runtime error paths still need conversion to the product explanation format without raw technical text.
FILES_CHANGED: `ui_luminifera/work/dashboard.py`; `ui_luminifera/states/`; `gui/main_window.py`; `tests/test_luminifera_work_states.py`; `tests/test_luminifera_states.py`

## STEP 12 - Developer Mode

STEP: 12
STATUS: PARTIAL; existing developer diagnostics remain opt-in, but a complete product-mode audit is deferred.
KNOWN_GAPS: Legacy diagnostic controls require a final visibility audit.

STEP 12 FOLLOW-UP: Product shell audit confirms normal navigation has no legacy technical toolbar, routing diagnostics or work-context controls; `developer_mode` remains disabled by default. Targeted shell/state tests: `6 passed`.

## STEP 13 - Visual Polish

STEP: 13
STATUS: PARTIAL; core Luminifera shell, backgrounds, transitions and readable product panels are implemented.
KNOWN_GAPS: Final typography, hover/focus and populated-state comparison require owner visual acceptance.

## STEP 14 - Window Size / Responsive

STEP: 14
STATUS: PARTIAL; product shell uses responsive layouts, stable panel sizing and has been checked in packaged Home previews at 1366x768, 1920x1080 and 2560x1440.
VISUAL_SCREENSHOTS: `Screenshots/responsive_1366x768.png`; `Screenshots/responsive_1920x1080.png`; `Screenshots/responsive_2560x1440.png`
KNOWN_GAPS: Final owner visual acceptance remains required for wide-screen composition and populated states.

## STEP 15 - Legacy Purge

STEP: 15
STATUS: PARTIAL; normal Product Mode now routes through Luminifera surfaces, product localization is readable in RU/UA/EN for the rebuilt screens, while legacy dialogs remain available as runtime fallbacks.
KNOWN_GAPS: A final string/import audit is required before deleting or hiding every legacy path.

## STEP 16 - Final Engine Parity

STEP: 16
STATUS: PASS for automated RC baseline; manual acceptance remains pending.
EVIDENCE: `EngineParity/FINAL.md`

## STEP 17 - Final Product Acceptance Build

STEP: 17
STATUS: PARTIAL; packaged executable and isolated smoke scenarios pass, but full pytest is blocked by pre-existing hanging GUI/subprocess tests and manual visual acceptance is pending.
EVIDENCE: `Screenshots/final_home.json`, `Screenshots/final_profile.json`, `Screenshots/final3_profile.json`, `EngineParity/FINAL.md`

## RUN COMPLETION CHECK - Product localization and artifact compatibility

STEP: 17 follow-up
STATUS: PASS for this implementation slice; visual review remains owner responsibility.
TECHNICAL_TESTS: 13 focused Luminifera/team/startup/work tests passed; artifact access keeps the canonical `artifact_type` field and remains compatible with legacy `kind` readers.
PACKAGED_TEST: PASS; rebuilt `dist/Team2050/Team2050.exe`; Team Builder and Settings previews exited with code 0 and `checks_passed=true`.
ENGINE_PARITY: No runtime/provider code paths changed; database artifact query now exposes an explicit compatibility alias.
VISUAL_SCREENSHOT: `Screenshots/team_builder_recheck.png`; `Screenshots/settings_recheck.png`
KNOWN_GAPS: Full legacy pytest still has the previously recorded hanging GUI/subprocess segment; final manual visual acceptance and complete legacy purge remain open.
FILES_CHANGED: `ui_luminifera/team/builder.py`; `ui_luminifera/settings/dialog.py`; `core/database.py`

STATE COPY: Added a shared RU/UA/EN Product Mode state catalog for provider-unavailable, worker-timeout and blocked-work conditions. Chat provider failures now show safe, actionable user copy while technical details remain in the event log; timeout activity uses the same product language. Targeted tests: `14 passed`; packaged Work/state smoke: `exit=0`, `checks_passed=true` (`Screenshots/states_recheck.png`).

VISUAL POLISH: Added explicit focus, disabled and progress-bar styling for the Luminifera Product Mode controls, preserving readable contrast and keyboard focus visibility. Targeted theme/shell/work tests: `7 passed`; rebuilt packaged Work preview: `exit=0`, `checks_passed=true` (`Screenshots/visual_polish_recheck.png`).

STATE CATALOG: Expanded the shared state catalog to cover sign-in required, failed/recoverable goal, no organization/team/files and destructive confirmation states in RU/UA/EN. Targeted state/shell tests: `6 passed`; packaged Work smoke after rebuild: `exit=0`, `checks_passed=true` (`Screenshots/state_catalog_recheck.png`).

LEGACY AUDIT: Added `LEGACY_UI_MAP.md` documenting retained compatibility surfaces, their service boundaries and Product Mode replacements. Verified the default `MainWindow` path is `LuminiferaShell`; legacy diagnostics and admin controls are not mounted in the Product shell.

PACKAGED ACCEPTANCE: Rebuilt `Team2050.exe` and exercised clean isolated profiles for onboarding, Home, Iris, Team Builder, Team roster, Work, Chat, Files, Settings and Profile. All ten smoke reports exited 0 with `checks_passed=true`; screenshots are indexed in `Screenshots/SCREENSHOT_INDEX.md`.

TEAM CARDS: Team roster cards now expose real lifecycle status and up to three assigned skill package names sourced through the agent directory/database service. No provider or internal ID is shown. Targeted roster/startup tests: `13 passed`; packaged roster smoke: `exit=0`, `checks_passed=true` (`Screenshots/team_skills_recheck.png`).

ENGINE PARITY RECHECK: Fresh `.venv\\Scripts\\python.exe -m pytest tests/runtime_v2 tests/runtime_v3` passed `71/71` in `1.62s`; packaged acceptance matrix now has 10 reports with zero failures. Updated `EngineParity/FINAL.md` and `FINAL_REPORT.md` with the current evidence.

FINALIZATION_NOTE: Rebuilt packaged Settings preview after replacing the default dialog button text; screenshot now shows localized `Сохранить` and `Отмена`, with packaged exit code 0 and `checks_passed=true`.

## Product language refresh follow-up

STEP: 09/13
STATUS: PASS for live Product Mode refresh.
TECHNICAL_TESTS: `13 passed` across shell, Home/Work/Files, startup and state coverage.
PACKAGED_TEST: PASS; rebuilt packaged executable and generated `Screenshots/language_recheck.json` with `checks_passed=true`.
ENGINE_PARITY: No runtime behavior changed; current Home/Work/Files view snapshots are retained while language labels are refreshed.
VISUAL_SCREENSHOT: `Screenshots/language_recheck.png`
KNOWN_GAPS: Final populated-state visual acceptance and legacy fallback purge remain documented in the final report.
FILES_CHANGED: `ui_luminifera/app_shell/shell.py`; `ui_luminifera/home/dashboard.py`; `ui_luminifera/work/dashboard.py`; `ui_luminifera/files/browser.py`

## Iris first-run outcome flow

STEP: 04/05
STATUS: PASS for the first-run handoff.
TECHNICAL_TESTS: Supervisor/Iris and Luminifera targeted suite passed (`18 passed`).
PACKAGED_TEST: PASS; rebuilt `Team2050.exe`; packaged Iris preview exited 0 with `checks_passed=true`.
ENGINE_PARITY: Free-form first-run requests now return a service-owned `team_proposal` result; the UI offers `Собрать команду` and forwards the original brief to Team Builder.
VISUAL_SCREENSHOT: `Screenshots/iris_recheck.png`
KNOWN_GAPS: Existing-organizations goal creation still uses the established explicit Goal commands; final full acceptance and legacy fallback audit remain open.
FILES_CHANGED: `core/supervisor_chat_service.py`; `gui/supervisor_chat_dialog.py`; `gui/main_window.py`; `tests/test_supervisor_chat_application_service.py`

FOLLOW_UP: First-run team handoff is now intent-gated: social greetings remain ordinary Iris help, while outcome-oriented descriptions expose the Team Builder action. Rebuilt packaged Iris smoke after the guard (`exit=0`, `checks_passed=true`).

FOLLOW_UP: `team_proposal` now carries the original first-run brief to the Team Builder; ordinary social messages remain `help`. Added regression coverage for both branches (`13 passed` targeted Supervisor/Iris/Product suite).

PRODUCT POLISH: Files cards now translate artifact types and review statuses into user-facing labels for RU/UA/EN. Targeted Files/Work/Supervisor tests: `11 passed`; packaged Files smoke: `exit=0`, `checks_passed=true` (`Screenshots/files_metadata_recheck.png`).

WORK OBSERVABILITY: Work view now includes persisted plan assignments as human-readable stages alongside progress, artifacts and review count. Targeted Work/UI tests: `5 passed`; packaged Work smoke: `exit=0`, `checks_passed=true` (`Screenshots/work_steps_recheck.png`).

TEAM VISIBILITY: Added a Product Mode Team screen with a readable roster, avatar, role and responsibility, connected to organization-filtered chat agents through the existing directory/application boundary. Targeted UI/startup tests: `13 passed`; packaged roster smoke: `exit=0`, `checks_passed=true` (`Screenshots/team_roster_recheck.png`).

TEAM RECOVERY: Empty Team state now exposes a localized `Собрать команду` action that opens the existing Team Builder, so a user who skipped onboarding can recover into team setup without internal commands. Targeted tests: `12 passed`; packaged roster smoke: `exit=0`, `checks_passed=true` (`Screenshots/team_roster_cta_recheck.png`).
IRIS PRODUCT SAFETY: Iris application failures now return a stable user-facing message without exception text; unavailable Strong routing no longer exposes provider internals; plan lists use human-readable statuses without plan IDs. Targeted tests: `16 passed`; packaged Iris smoke: `exit=0`, `checks_passed=true` (`Screenshots/iris_safety_recheck.json`, `Screenshots/iris_safety_recheck.png`).
WORK V3 VISIBILITY: Luminifera Work read-only service now projects the latest durable Runtime V3 checkpoint into the product view, including goal state, computed progress, artifacts, findings and work steps; legacy task-table fallback remains available. Targeted tests: `14 passed`; packaged Work smoke: `exit=0`, `checks_passed=true` (`Screenshots/work_v3_checkpoint_recheck.json`, `Screenshots/work_v3_checkpoint_recheck.png`).
HOME V3 VISIBILITY: Home now consumes the same durable Runtime V3 projection as Work, so the active goal, progress and recent artifacts remain visible from the first product screen after real execution. Targeted tests: `15 passed`; packaged Home smoke: `exit=0`, `checks_passed=true` (`Screenshots/home_v3_checkpoint_recheck.json`, `Screenshots/home_v3_checkpoint_recheck.png`).
WORK RECEIPT: Work now exposes a dedicated verified-result card. It is marked ready only when a completed Runtime V3 goal has a durable WorkReceipt with artifact and evidence references; otherwise the card clearly says review is pending. Targeted tests: `16 passed`; packaged Work smoke: `exit=0`, `checks_passed=true` (`Screenshots/work_receipt_recheck.json`, `Screenshots/work_receipt_recheck.png`).
FILES V3 VISIBILITY: Files now projects durable Runtime V3 artifacts alongside legacy artifacts, deduplicated by product filename and sanitized to basename-only labels. Targeted tests: `17 passed`; packaged Files smoke: `exit=0`, `checks_passed=true` (`Screenshots/files_v3_checkpoint_recheck.json`, `Screenshots/files_v3_checkpoint_recheck.png`).
PRODUCT STATE SAFETY: Work maps RUNNING, REWORK, FAILED and unknown goal/step states to localized human-readable copy; raw runtime enum values no longer leak into Product Mode. Targeted tests: `10 passed`; packaged Work smoke: `exit=0`, `checks_passed=true` (`Screenshots/work_state_labels_recheck.json`, `Screenshots/work_state_labels_recheck.png`).
RESULT HANDOFF: Work now offers an explicit `Открыть результат` action only when the verified receipt is ready; it navigates to the product Files view. The action is hidden while review is pending. Luminifera test suite: `27 passed`; packaged Work smoke: `exit=0`, `checks_passed=true` (`Screenshots/work_result_action_recheck.json`, `Screenshots/work_result_action_recheck.png`).
NAVIGATION STATE: Direct product transitions now update the active sidebar item themselves, keeping navigation selection synchronized when Work/Files are opened from contextual actions. Targeted tests: `16 passed`; packaged Work smoke: `exit=0`, `checks_passed=true` (`Screenshots/work_nav_recheck.json`, `Screenshots/work_nav_recheck.png`).

## Iris Runtime V3 goal handoff

STEP: 04/06 integration follow-up
STATUS: PASS for Iris-to-Runtime-V3 goal handoff.
TECHNICAL_TESTS: `28 passed` across Luminifera and Supervisor application-service tests; dedicated goal-handler regression confirms the organization context and objective are forwarded.
PACKAGED_TEST: PASS; rebuilt `dist/Team2050/Team2050.exe`; isolated Iris preview exited with code 0 and `checks_passed=true` (`Screenshots/iris_runtime_goal_recheck.json`).
ENGINE_PARITY: Iris goal creation now uses the existing `RuntimeV3GoalService` boundary when available, so durable goal/work/artifact projections remain shared with Chat, Home, Work and Files. Legacy plan handling remains as compatibility fallback when no V3 handler is supplied.
VISUAL_SCREENSHOT: `Screenshots/iris_runtime_goal_recheck.png`
KNOWN_GAPS: Full legacy pytest and owner manual visual acceptance remain documented as open; no new Product Mode internals were exposed.
FILES_CHANGED: `core/supervisor_chat_service.py`; `gui/main_window.py`; `tests/test_supervisor_chat_application_service.py`

## Persistent Iris product window

STEP: 04/06 integration follow-up
STATUS: PASS for persistent owner workspace behavior.
TECHNICAL_TESTS: `29 passed` across Luminifera, Iris dialog and Supervisor application-service tests; source modules compile with the project virtual environment.
PACKAGED_TEST: PASS; rebuilt `dist/Team2050/Team2050.exe`; isolated Iris and Work previews exited with code 0 and `checks_passed=true` (`Screenshots/iris_persistent_recheck.json`, `Screenshots/home_after_iris_recheck.json`).
ENGINE_PARITY: The Iris window is now reused while open, preserves its conversation context, updates organization context when the user switches workspace, and opens non-modally from Product Mode. Runtime behavior remains service-backed.
VISUAL_SCREENSHOT: `Screenshots/iris_persistent_recheck.png`
KNOWN_GAPS: Manual owner visual acceptance and the previously documented hanging legacy GUI/subprocess tests remain open.
FILES_CHANGED: `gui/main_window.py`

## Product connection-status localization

STEP: 09 follow-up
STATUS: PASS for RU/UA/EN connection-status copy.
TECHNICAL_TESTS: `32 passed` across the focused Luminifera/Iris suite; provider status labels are asserted for all supported interface languages.
PACKAGED_TEST: PASS; rebuilt `dist/Team2050/Team2050.exe`; isolated Settings preview exited with code 0 and `checks_passed=true` (`Screenshots/settings_localized_recheck.json`).
ENGINE_PARITY: No provider or runtime behavior changed; only Product Mode presentation strings were localized.
VISUAL_SCREENSHOT: `Screenshots/settings_localized_recheck.png`
KNOWN_GAPS: Legacy diagnostics remain behind the documented fallback; final manual visual acceptance is still required.
FILES_CHANGED: `ui_luminifera/settings/dialog.py`; `tests/test_luminifera_settings.py`

## Runtime result refresh and team visibility

STEP: 06 follow-up
STATUS: PASS for Product Mode refresh after a Runtime V3 goal.
TECHNICAL_TESTS: `51 passed` across Luminifera, Iris and MainWindow helper tests; durable checkpoint inspection confirms `3` employee snapshots, `1` goal, artifacts and evidence are available to the Work adapter.
PACKAGED_TEST: Build PASS. A repeated packaged golden run entered the real GUI path and opened Work, but its external Codex/Gemini calls timed out before review; that run is recorded as FAIL and is not used as acceptance evidence.
ENGINE_PARITY: After V3 execution, Home/Work/Files projections are refreshed in the same application flow. Work uses durable employee snapshots for team size and no longer reports zero participants for a populated goal.
VISUAL_SCREENSHOT: Work rendering is covered by the existing packaged `Screenshots/work_v3_checkpoint_recheck.png`; the latest failed provider run is intentionally not promoted as PASS evidence.
KNOWN_GAPS: Packaged external provider timeouts remain an infrastructure/runtime issue requiring provider availability or timeout policy work; full legacy pytest and owner manual visual acceptance remain open.
FILES_CHANGED: `gui/main_window.py`; `core/luminifera_work_service.py`; `tests/test_main_window_helpers.py`; `tests/test_luminifera_work_service.py`

## Luminifera V2 closed-alpha completion

TASK: LUMINIFERA V2 PRODUCT COMPLETION — packaged product flow and one V2 UI stack.
STATUS: READY_FOR_OWNER_ALPHA_TEST; Final Alpha PASS not declared.
IMPLEMENTATION: Generic Iris team creation now selects an operational template with a director instead of the non-executable advisory board. Product Mode uses the V2 Home/Iris/Team/Work/Files/Settings stack; legacy Product renderers are no longer loaded by `app.html`.
VERIFIED: Fresh packaged launch created a workspace through the UI, Iris created a team, a real Goal was created and executed, Runtime V3 produced WorkItems/artifacts/evidence, Files displayed the resulting artifacts, Feedback was submitted in Settings and remained after reload. Targeted suite: `36 passed`; isolated Web smoke: `checks_passed=true`; packaged build: PASS; visual capture manifest: `unavailable=[]`.
EVIDENCE: `QA/LuminiferaRebuild/V2/closed-alpha/web-smoke-0830.json`; `QA/LuminiferaRebuild/V2/closed-alpha/captures-final/manifest.json`; `QA/LuminiferaRebuild/V2/closed-alpha/captures-final/`; `dist/Luminifera.exe`.
KNOWN_LIMITATION: The product capture runner is diagnostic-only and does not mutate application data. Final owner hands-on validation remains required; Final Alpha PASS is intentionally not declared.
FILES_CHANGED: `apps/web/static/app.html`; `apps/web/static/product-v2.js`; `apps/web/static/v2.css`; `core/supervisor_chat_service.py`; `scripts/capture_visual_gate.py`; `tests/test_alpha_product_ui.py`

## Product UI V2 milestone

TASK: Home, Iris and Work rebuilt as the first Product UI milestone over the existing Core/API; legacy Team/Files/Settings renderers remain unchanged pending review.
STATUS: READY_FOR_HUMAN_VISUAL_REVIEW pending V2 acceptance; Final Alpha PASS not declared.
IMPLEMENTATION: Added real-data Product UI V2 composition and styling for Home/Iris/Work. Iris keeps the existing chat composer and API history; Work renders durable goals and starts them through `/api/goals/{plan_id}/start`; no database or runtime rewrite.
VERIFIED: Packaged `dist/Luminifera.exe` launched and served the V2 UI. Browser smoke confirmed Home, Iris and Work render; Iris sent `Привет` and received a persisted Iris reply. Isolated `scripts/web_smoke.py` passed with team creation, goal creation/start, 3 WorkItems, 2 artifacts, 4 evidence and restart persistence. `scripts/capture_visual_gate.py` captured all screens with `unavailable=[]`.
EVIDENCE: `QA/LuminiferaRebuild/V2/LUMINIFERA_PRODUCT_V2_CAPTURES.zip`, `QA/LuminiferaRebuild/V2/captures/manifest.json`, `QA/LuminiferaRebuild/v2_web_smoke.json`.
KNOWN_LIMITATION: Existing legacy profile contains organizations without assigned directors; those records are rejected by the existing goal service. The isolated clean-profile flow passes. Full pytest and final commit/push follow after targeted regression verification.
FILES_CHANGED: `apps/web/static/app.html`; `apps/web/static/product-v2.js`; `apps/web/static/v2.css`; `scripts/capture_visual_gate.py`

## Luminifera UI Shell V3 integration

TASK: INTEGRATE LUMINIFERA UI SHELL V3.
STATUS: READY_FOR_OWNER_HANDS_ON_TEST.
IMPLEMENTATION: Imported the supplied V3 shell as the sole Product UI and connected Home, Team, Work, Files and Settings to the real Application API through `window.LuminiferaBridge`. Iris remains inline on Home; workspace selection, social chat, action intent, goal start, artifacts, feedback and media configuration are service-backed. No fake data or raw runtime/provider plumbing is rendered.
VERIFIED: Packaged `dist/Luminifera.exe` launched in an isolated profile. UI E2E created a workspace, received an Iris social reply without a Goal, created a real operational team, created and started a Goal, displayed real artifacts in Files, and submitted Feedback. V3 capture runner produced `unavailable=[]`. Node syntax checks passed for V3 scripts; targeted UI/shell tests passed.
EVIDENCE: `QA/LuminiferaRebuild/V3/captures/manifest.json`; `QA/LuminiferaRebuild/V3/captures/`; `dist/Luminifera.exe`.
KNOWN_LIMITATION: Final owner hands-on visual acceptance remains required; capture runner uses an isolated read-only browser profile and does not mutate product data.
FILES_CHANGED: `apps/web/static/app.html`; `apps/web/static/v3/`; `scripts/capture_visual_gate.py`; `tests/test_alpha_product_ui.py`

## Packaged V3 diagnostic mode

TASK: Add hidden `?diagnostics=1` mode for packaged V3.
STATUS: PASS; READY_FOR_OWNER_HANDS-ON_TEST_2.
IMPLEMENTATION: Added a query-gated diagnostic panel and a read-only Bridge probe. It reports API reachability, current organization name, Iris/team/work/files/feedback endpoint status and configured media sources without secrets, raw IDs or runtime/provider plumbing. Normal `/app` remains unchanged.
VERIFIED: Packaged diagnostic URL showed HTTP 200 for API and all product services; normal URL kept the panel hidden and global scroll absent. Full pytest: `550 passed, 2 warnings`; targeted static UI test included.
EVIDENCE: `QA/LuminiferaRebuild/V3/DIAGNOSTIC_MODE_2026-08-31.md`.
FILES_CHANGED: `apps/web/static/app.html`; `apps/web/static/v3/index.html`; `apps/web/static/v3/app.js`; `apps/web/static/v3/bridge.js`; `tests/test_alpha_product_ui.py`

## V3 owner-style preflight

TASK: HOLD FOR OWNER HANDS-ON TEST - packaged preflight for V3 baseline.
STATUS: READY_FOR_OWNER_HANDS_ON_TEST_2.
VERIFIED: Packaged `dist/Luminifera.exe` checked at `1920x1080` and `1440x900`; Home, Team, Work, Files and Settings activated; background and Iris media loaded from `config.js`; Iris remained inline; honest empty states rendered; global vertical scroll absent; no product defect found.
FIX: Extended the diagnostic capture runner with `--width` and `--height` arguments. No Product UI or runtime redesign changes were made.
EVIDENCE: `QA/LuminiferaRebuild/V3/OWNER_PREFLIGHT_2026-08-31.md`; `QA/LuminiferaRebuild/V3/captures/preflight-1920/manifest.json`; `QA/LuminiferaRebuild/V3/captures/preflight-1440/manifest.json`.

## Packaged Iris conversational gate

TASK: Verify Iris social conversation and real action intent in packaged V3.
STATUS: PASS; packaged context gate and full regression completed.
FIX: Added `Собери мне команду`, `Собрать команду`, `assemble team` and related UI paraphrases to the existing Supervisor application boundary. Social messages remain non-operational.
VERIFIED: Packaged `Собери мне команду` created a real operational team; `Привет` and `Как дела?` returned conversational responses and left work inactive. Targeted tests passed.
VERIFIED: Packaged GUI tested team action, social messages, pending cancellation and no-pending confirmation. Targeted 65 passed; full pytest `552 passed, 2 warnings`.
EVIDENCE: `QA/LuminiferaRebuild/V3/IRIS_CONVERSATIONAL_GATE_2026-08-31.md`.

## Fresh-profile onboarding V3

TASK: Verify first launch, Iris workspace creation, reload persistence and honest empty states.
STATUS: PASS; packaged onboarding and full regression completed.
FIX: After Iris creates an organization, V3 reloads the real workspace list and activates the returned organization instead of leaving the UI in the empty state.
VERIFIED: Empty packaged profile, `Создай организацию: Fresh Onboarding`, persisted Iris context after reload, all Product routes and no global scroll. Targeted 40 passed; full pytest `553 passed, 2 warnings`.
EVIDENCE: `QA/LuminiferaRebuild/V3/FRESH_ONBOARDING_2026-08-31.md`.

## Packaged V3 media gate

TASK: Verify config.js image/video media, reload/restart behavior and missing-resource fallback.
STATUS: PASS; packaged media gate and full regression completed.
FIX: Added error handling for background/Iris image and video resources. A configured poster is used when available; otherwise the styled media container safely clears the broken element. Wired `Перечитать config.js` to a real reload.
VERIFIED: Packaged image mode, video element creation, missing-video poster fallback, restoration after reload and no global scroll. Targeted 21 passed; full pytest `554 passed, 2 warnings`.
   EVIDENCE: `QA/LuminiferaRebuild/V3/MEDIA_GATE_2026-08-31.md`.

## Packaged V3 failure/recovery gate

TASK: Verify honest recovery when API/LLM/media are temporarily unavailable.
STATUS: PASS for the packaged API failure/retry path; full regression PASS.
FIX: Added bounded API and diagnostics requests with AbortController timeouts and an initial-load catch that presents a user-facing unavailable-engine state. Existing chat and media fallbacks remain active.
VERIFIED: Packaged API endpoint abort produced a responsive honest error state; restoring the endpoint and clicking Обновить rendered Home again without data loss. After packaged stop/relaunch, the completed goal remained at 100% with two verified artifacts; Work and Files rendered without duplicate rows. Targeted 9 passed; full pytest 555 passed, 2 warnings.
EVIDENCE: `QA/LuminiferaRebuild/V3/RECOVERY_GATE_2026-08-31.md`.

## Packaged V3 multi-workspace isolation gate

TASK: Verify organization isolation, workspace switching and selected-workspace persistence.
STATUS: PASS; packaged gate completed.
FIX: Persisted the selected workspace ID in localStorage and restored it only against the current organization list.
VERIFIED: Two packaged workspaces returned distinct organizations, team counts, files and chat counts; switching did not leak data; reload restored the selected workspace; global scroll absent. Targeted 10 passed; full pytest 556 passed, 2 warnings.
EVIDENCE: `QA/LuminiferaRebuild/V3/MULTI_WORKSPACE_2026-08-31.md`; `QA/LuminiferaRebuild/V3/multi-workspace-isolation.png`.

## V3 permissions and role-bound gate

TASK: Verify real permissions, role boundaries, denial behavior and cross-workspace restrictions.
STATUS: PASS; no defect found and no runtime change required.
VERIFIED: Targeted capability, runtime, management, organization-isolation and Web API tests passed; packaged UI smoke exposed no raw IDs and no global scroll. Targeted 71 passed, 1 warning.
EVIDENCE: `QA/LuminiferaRebuild/V3/PERMISSIONS_ROLE_BOUND_2026-08-31.md`.

## Packaged V3 all-controls gate

TASK: Verify every visible V3 control has a real action or honest state.
STATUS: PASS; packaged E2E completed.
FIX: Explicitly cancel and close the organization dialog close control so the form submit handler cannot intercept it.
VERIFIED: Hero Iris, prompt, profile, workspace dialog open/close, all five routes, packaged rendering and no-global-scroll passed. Targeted 11 passed; full pytest 557 passed, 2 warnings.
EVIDENCE: `QA/LuminiferaRebuild/V3/ALL_CONTROLS_2026-08-31.md`; `QA/LuminiferaRebuild/V3/all-controls-gate.png`.

## V3 owner-ready polish gate

TASK: Owner-style preflight at 1920x1080 and 1440x900; fix only concrete visual or UX defects.
STATUS: PASS; packaged preflight completed.
FIX: Organization dialog close interception was corrected in the all-controls gate; no additional visual defects were found.
VERIFIED: Text fit, spacing, contrast, focus/hover, honest states, navigation and no-global-scroll checked in both packaged captures. Targeted 11 passed; full pytest 557 passed, 2 warnings.
EVIDENCE: `QA/LuminiferaRebuild/V3/OWNER_READY_POLISH_2026-08-31.md`; `owner-polish-1920.png`; `owner-polish-1440.png`; `all-controls-gate.png`.
