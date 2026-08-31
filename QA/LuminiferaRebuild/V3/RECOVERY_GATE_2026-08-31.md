# V3 recovery gate - 2026-08-31

## Packaged build

- Binary: `dist/Luminifera.exe`
- URL under test: `http://127.0.0.1:57703/app`

## Checks

- API failure was simulated in the packaged browser with the organizations endpoint aborted.
- The product stayed responsive and displayed `Движок временно недоступен` with a retry instruction.
- The endpoint was restored and `Обновить` was clicked; the Home state rendered again with no data loss.
- Requests now have bounded timeouts: 10 seconds for normal API calls and 5 seconds for diagnostics probes.
- Media failure fallback remains covered by the existing packaged media gate.
- No design changes or fake data were introduced.

## Result

PASS. Targeted UI recovery tests: 9 passed. Full pytest: 555 passed, 2 warnings.
