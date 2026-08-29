# Luminifera engine parity

Automated RC evidence from the packaged isolated profile confirms:

- organization isolation: PASS;
- team activation: PASS;
- social mode without goal: PASS;
- real goal with artifacts and observations: PASS;
- restart recovery: PASS;
- employee deletion: PASS;
- knowledge retention: PASS;
- SQLite foreign-key check: PASS, `foreign_key_errors=0` (`FK=[]`).

The product UI reads this state through application services; runtime/provider/orchestration services were not replaced by UI mocks.

Targeted runtime verification: `tests/runtime_v2` and `tests/runtime_v3` passed, 71 tests in 1.66s.

Latest verification (2026-08-29): `.venv\\Scripts\\python.exe -m pytest tests/runtime_v2 tests/runtime_v3` passed `71/71` in `1.62s`. Packaged Luminifera acceptance matrix covered onboarding, Home, Iris, Team Builder, Team roster, Work, Chat, Files, Settings and Profile; all ten isolated reports returned `checks_passed=true`.
