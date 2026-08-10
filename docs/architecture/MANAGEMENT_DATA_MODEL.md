# Management Data Model

Phase 1 adds management foundations without implementing full production UI.

## Tables

```text
role_profiles
agent_profiles
agent_role_assignments
agent_permissions
agent_permission_denies
management_audit_events
provider_definitions
provider_installations
provider_accounts
provider_capabilities
provider_health_checks
provider_install_events
provider_auth_events
agent_provider_assignments
provisioning_sessions
provisioning_steps
```

## Existing Related Tables

```text
projects
tasks
task_transitions
agent_runs
audit_events
approvals
findings
artifacts
skill_usage
knowledge_usage
standard_usage
reference_design_usage
```

## Agent Profile

```text
agent_id
display_name
description
lifecycle_state
provider_id
persona_id
avatar_path
schema_version
created_at
updated_at
```

## Role Profile

```text
role_id
display_name
description
responsibilities
restrictions
schema_version
created_at
updated_at
```

## Management Audit Event

```text
actor
object_type
object_id
action
previous_value
new_value
files_changed
database_changes
affected_employees
reason
approval
rollback_status
timestamp
```

## Safe Configuration Repository

Phase 1 adds `ConfigurationRepository`, rooted at the app user data management directory. It provides:

- root enforcement;
- path traversal protection;
- JSON read;
- atomic JSON write;
- dry-run path validation.

Future export/import must not include secrets or provider tokens.

## Phase 2A UI Data Flow

```text
Команда button
  -> DirectorConsoleDialog
  -> ManagementService
  -> Database + ConfigurationRepository
```

The GUI never writes SQLite or JSON directly.

## Provider Provisioning Data

Provider tables store definitions, installation metadata, safe account metadata, health checks and employee assignments. They do not store provider secrets.
