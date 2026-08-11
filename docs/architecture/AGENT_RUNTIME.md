# Agent Runtime

Runtime state is provider-independent and belongs to the employee identity.
U1 records:

- current task;
- current operation;
- current plan/checkpoint;
- active artifacts and open findings when supplied;
- status such as `IDLE`, `WORKING` or `BLOCKED`.

The task orchestrator updates the state when a registered employee run starts
and when it records a result. Legacy router-only tests and installations without
an employee profile remain valid; they simply have no runtime row yet.

Provider adapters execute runs. They do not own identity, organization
membership, skills or handoff state.
