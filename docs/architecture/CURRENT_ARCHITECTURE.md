# Current Architecture - Roman 2050

Date: 2026-07-31

Roman 2050 is a standalone Windows desktop chat client written in Python with PySide6. It presents a group chat named "Otdel vazhnykh del" and connects two CLI-backed agents: Roman through Codex CLI and Petr through Gemini CLI.

## Entry Points

- `app.py` creates `SettingsService`, configures logging, starts `QApplication` and opens `MainWindow`.
- `scripts/build_windows.bat` builds the desktop executable with PyInstaller.
- Tests are under `tests/` and run through `pytest`.

## Current Runtime Flow

1. User submits text in `ChatWidget`.
2. `MainWindow.send_message()` stores the user message in SQLite.
3. `MainWindow` applies routing and autonomy heuristics.
4. `MainWindow._start_next_agent_run()` builds a `PromptBuilder`, selects `CodexClient` or `GeminiClient`, creates `GenerateWorker`, and starts a Qt thread.
5. `GenerateWorker` builds the prompt and calls the selected CLI client.
6. The GUI receives stream deltas/statuses and displays them.
7. `MainWindow._generation_finished()` cleans/splits the response, stores messages, updates skills and schedules possible peer handoff.

## Existing Components

- `MainWindow`: GUI controller plus current routing, autonomy sequencing, run lifecycle and some workflow policy.
- `PromptBuilder`: assembles identity, timeline, memory, skills, selected context snapshot, peer context and autonomy instructions.
- `Autonomy`: natural-language heuristics for stop commands, autonomous discussion, handoff and unfinished work.
- `SkillService`: JSON-backed lightweight memory for agent skills.
- `Database`: SQLite persistence for conversations, messages, memories and app events.
- `CodexClient`: subprocess wrapper for Codex CLI, including streaming and status extraction.
- `GeminiClient`: subprocess wrapper for Gemini CLI.
- `WorkspaceService`: local workspace preparation for Codex/Gemini runtime folders.

## Current Risks

- `MainWindow` contains too much application logic.
- Chat text is still the main source for routing and completion heuristics.
- Skills are stored in one simple JSON file, not a portable engineering knowledge system.
- There was no first-class task/run state before Phase 1.
- Agent responses were unstructured and not auditable as workflow evidence.
- True parallel agent execution is not implemented; the current model is sequential.

## Difference From Conceptual Target

The existing app is a working chat client, not yet a controlled engineering workflow system. Phase 1 adds foundations while preserving the Roman/Petr behavior.
