# Employee Execution Readiness

Employee lifecycle and execution readiness are separate.

Example:

```text
lifecycle: ACTIVE
readiness: AUTHENTICATION_REQUIRED
```

## Readiness States

```text
PROFILE_INCOMPLETE
PROVIDER_NOT_ASSIGNED
PROVIDER_NOT_INSTALLED
INSTALLATION_REQUIRED
AUTHENTICATION_REQUIRED
ACCESS_CHECK_REQUIRED
PLAN_INCOMPATIBLE
CAPABILITY_TEST_REQUIRED
READY
DEGRADED
BLOCKED
SETUP_FAILED
```

## Phase 2A.1 Calculation

`ProviderProvisioningService.readiness_for_employee()` checks:

- profile exists;
- lifecycle allows routing;
- provider is assigned;
- latest provider health;
- installation status;
- authentication status;
- access status;
- capability status.

Router enforcement is not fully migrated in this phase, but Director Console displays readiness.

## Future Router Rule

The agent router must not assign engineering work to employees unless readiness permits it.
