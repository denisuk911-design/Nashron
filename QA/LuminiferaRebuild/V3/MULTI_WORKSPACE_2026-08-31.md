# V3 multi-workspace isolation - 2026-08-31

## Packaged build

- Binary: `dist/Luminifera.exe`
- Packaged URL under test: `http://127.0.0.1:58210/app`

## Checks

- Workspace A `ORG-89510E4F6FB1` returned its own organization, 4 team members, 2 files and 2 chat messages.
- Workspace B `ORG-D2B0DB9B94A4` returned its own organization, 6 team members, 0 files and 0 chat messages.
- Switching A -> B did not leak team, files or chat state.
- Selecting A persisted `luminifera.organizationId`; after browser reload the selected workspace and A counts remained unchanged.
- Packaged UI had no global vertical scroll.

## Result

PASS. Workspace selection is persisted in localStorage and restored only when the stored organization is present in the API response. The UI continues to use organization-scoped Application API requests.
