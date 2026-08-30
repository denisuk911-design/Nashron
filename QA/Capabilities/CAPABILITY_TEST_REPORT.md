# Capability Test Report

Status: `IMPLEMENTED - targeted PASS`
Date: 2026-08-30

## Verified

- capability contracts are independent of provider/runtime names;
- two implementations of one capability can be registered;
- router selects by privacy and historical reliability;
- failed primary uses a compatible fallback;
- unavailable capability returns an explicit failure;
- permissions are checked before executor invocation;
- Iris requests a capability without knowing tool/provider names;
- normalized capability/tool events are emitted;
- tool usage duration and returned usage metrics are preserved;
- WebCore wires an honest empty registry by default;
- existing runtime tests remain covered by the targeted suite.

## Command

```text
.venv\\Scripts\\python.exe -m pytest -q tests/test_capability_layer.py tests/test_runtime_contracts.py tests/test_iris_orchestration_service.py tests/test_runtime_selector.py tests/test_runtime_execution_service.py
```

Result: targeted `44 passed in 12.50s`; full suite `544 passed in 177.61s`.

The full suite retains the two known non-fatal warnings: the Starlette/httpx
TestClient deprecation and the existing duplicate ZIP-entry warning in the
tampered-backup regression.

## Remaining work

Real tool services must be registered before a capability becomes available in
Beta. Until then the router returns `NOT_AVAILABLE`; no fake PASS is claimed.
