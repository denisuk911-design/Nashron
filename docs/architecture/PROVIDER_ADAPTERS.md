# Provider Adapters

Provider-specific detection and future provisioning must stay inside adapters, not `MainWindow` or employee wizard code.

## Current Adapters

- `CodexProviderAdapter`
- `GeminiProviderAdapter`
- `MissingProviderAdapter`

Implemented in `core/provider_service.py`.

## Target Adapter Interface

Future adapters should support:

```text
detect_installation()
get_installed_version()
validate_version()
build_install_plan()
execute_install_plan()
verify_installation()
start_authentication()
get_authentication_status()
verify_access()
get_capabilities()
run_capability_probe()
create_agent_command()
redact_sensitive_output()
diagnose()
build_uninstall_plan()
```

## Phase 2A.1 Boundary

Only lightweight health checks are implemented. Install/auth/capability execution is deferred to Phase 2A.2.

## Provider Manifests

Built-in provider definitions are currently code-backed. Future manifest files should live under:

```text
providers/
  codex/provider.json
  gemini/provider.json
  claude/provider.json
```

Imported manifests must not execute arbitrary shell commands.
