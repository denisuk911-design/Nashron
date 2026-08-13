# Team2050 Runtime V2 Benchmark

This directory is an isolated, executable architecture prototype. It is not
imported by the desktop application and does not migrate the production runtime
or database.

## Run

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest -q experiments\runtime_v2\test_runtime_v2_benchmark.py
```

The prototype uses only the Python standard library and pytest from the existing
development environment. It creates temporary SQLite databases through pytest's
`tmp_path`; no user profile is read or changed.

## Executable contracts

- `CanonicalAgentState` is provider-neutral and survives JSON/SQLite restart.
- `ProviderAdapter` can switch from mock A to B without changing employee,
  capability, task, artifact or checkpoint identity.
- committed `effect_key` records prevent repeating a side effect after a crash.
- `StructuredHandoff` requires real artifact IDs and acceptance criteria.
- candidate skill versions run against a deterministic evaluation dataset and
  are promoted or rejected against the current version.
- validated organizational knowledge survives employee identity deletion and
  bootstraps a new employee in the same profession.
- traces capture provider switches, timeouts, tool failures, artifacts and
  results without depending on a cloud observability service.

See [RESEARCH_MATRIX.md](RESEARCH_MATRIX.md) for upstream comparison and
[ARCHITECTURE.md](ARCHITECTURE.md) for the target model and migration decision.

## Deliberate limits

- Providers are deterministic doubles; hidden reasoning and provider-private
  sessions are never treated as portable state.
- SQLite demonstrates contracts, not production scale.
- No framework adapter, real CLI provider or GUI integration is included.
- No production dependency, schema, router, prompt or chat behavior is changed.
