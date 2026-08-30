# Tool Registry Contract

Each registration contains a `CapabilityToolContract` and a callable executor.
The contract includes:

- capability and tool IDs;
- availability and health;
- required permissions;
- input/output schemas;
- cost and latency hints;
- privacy mode;
- internal provider metadata;
- historical reliability.

One capability may have multiple tool IDs. Registration rejects duplicate IDs,
and `replace` is explicit for controlled configuration changes. Tool executors
must return `ToolExecutionResult`; arbitrary or fabricated success values are
rejected by the router.

The Web/Core composition root owns the registry instance. Iris sees only
`CapabilityExecutionService.request(...)`; Product UI does not receive
provider-specific structures.
