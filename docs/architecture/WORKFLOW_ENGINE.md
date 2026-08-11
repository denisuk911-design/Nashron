# Workflow Engine Foundation

U1 uses a minimal deterministic `WorkflowDefinition` with ordered
`WorkflowStep` records. Each step names a responsibility, operation and
expected outputs. It is intentionally smaller than BPMN.

The engine boundary is:

```text
task intent -> select workflow -> select responsible role
            -> execute run -> record artifact/evidence -> review -> next step
```

The current implementation provides storage, creation and template linkage.
It does not silently invent completion, skip owner approvals or claim that a
provider performed a filesystem operation without evidence.
