# Packaged V3 fresh-profile onboarding

Build under test: `dist/Luminifera.exe` after the workspace activation fix.

## Scenario

- Started packaged client with an isolated empty `TEAM2050_HOME` profile.
- First launch showed one empty workspace option, no organization, no team data, no active work and an honest Iris empty state.
- Sent `Создай организацию: Fresh Onboarding` in the inline Iris chat.
- Iris returned `Организация «Fresh Onboarding» создана.` from the real chat/application service.
- V3 refreshed the workspace list and selected `Fresh Onboarding`; the Home summary showed the real organization and `0 сотрудников`.
- Sent `Привет, Iris`; both owner and Iris messages were persisted.
- Reloaded the packaged page. Workspace selection, organization name and both chat messages were restored.
- Home, Team, Work, Files and Settings routes all activated successfully; empty states contained no fake records and global vertical scroll was absent.

## Checks

- Initial empty profile: PASS.
- Iris workspace creation and automatic activation: PASS.
- Reload persistence of workspace and chat context: PASS.
- Product route preflight: PASS.
- Targeted tests: PASS.
