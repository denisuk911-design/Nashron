# Clean installation

The repository contains application templates only. Chat history, settings, logs and the local database are stored outside the repository in `%LOCALAPPDATA%\Roman2050`.

1. Download the repository from GitHub with `git clone` or the GitHub ZIP download.
2. Install Python 3.12+ and the required Codex/Gemini CLI providers.
3. Run `scripts\run_clean_windows.bat` for an isolated default profile in `%LOCALAPPDATA%\Roman2050-Clean`.
4. To remove that profile completely, run `scripts\reset_clean_profile_windows.bat` and confirm the prompt.

The clean script does not copy or import the old computer's database. The normal `scripts\run_windows.bat` continues using the regular profile.
