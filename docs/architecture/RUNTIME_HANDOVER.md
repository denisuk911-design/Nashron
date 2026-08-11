# Runtime Handover Boundary

Future provider or machine handover must transfer a checkpoint package, not
credentials or hidden process state:

```text
employee + task + plan + workflow step + artifacts + evidence + findings
       + approved context + required capabilities
```

The receiving runtime must acknowledge the checkpoint, validate capabilities,
continue from the recorded step and append an audit event. Secret values stay
in the local provider configuration. U1 defines the state foundation only;
cross-machine continuation is not implemented yet.
