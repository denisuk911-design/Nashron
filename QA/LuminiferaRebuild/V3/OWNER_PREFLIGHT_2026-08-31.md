# Owner-style preflight: V3 baseline

Baseline: `d88d34a Integrate Luminifera UI Shell V3`

## Result

Status: `READY_FOR_OWNER_HANDS_ON_TEST_2`

Packaged executable tested: `dist/Luminifera.exe`.

| Viewport | Screens | Media | Global scroll | Result |
| --- | --- | --- | --- | --- |
| 1920x1080 | Home, Team, Work, Files, Settings | background and Iris loaded from `config.js` | absent (`html/body: hidden`) | PASS |
| 1440x900 | Home, Team, Work, Files, Settings | background and Iris loaded from `config.js` | absent (`html/body: hidden`) | PASS |

Additional checks:

- Iris media is rendered inside the Home screen; no separate Iris messenger route is used.
- All five routes activated through the V3 navigation and rendered without unavailable states.
- Empty Team, Work and Files states use real-data copy and do not contain demo records.
- Workspace creation, chat, team creation, goal start, artifact listing and Feedback remain service-backed from the prior packaged E2E.
- No concrete product defect was found during this preflight. Only the diagnostic capture runner was extended with `--width` and `--height` so both required viewports are reproducible.

## Captures

- [1920x1080 manifest](captures/preflight-1920/manifest.json)
- [1920x1080 captures](captures/preflight-1920/)
- [1440x900 manifest](captures/preflight-1440/manifest.json)
- [1440x900 captures](captures/preflight-1440/)

## Verification

- `scripts/capture_visual_gate.py --width 1920 --height 1080`: `unavailable=[]`
- `scripts/capture_visual_gate.py --width 1440 --height 900`: `unavailable=[]`
- Direct packaged DOM preflight: both viewports PASS for routes, media, inline Iris and overflow.
