# Definition of Done

Source of truth: `docs/product/PRODUCT_NORTH_STAR.md`.

Use these statuses honestly:

- `IMPLEMENTED_WITH_LIMITATIONS`;
- `READY_FOR_USER_TEST`;
- `REWORK_REQUIRED`;
- `BLOCKED`.

Do not use `COMPLETE` before user validation.

## Major Feature Done Criteria

A major feature is ready only when:

1. It works through the interface.
2. It has explicit states.
3. It fails safely.
4. It is auditable.
5. It preserves existing behavior.
6. It has automated tests.
7. It has a user test plan.
8. It was tested in a real built application.
9. Limitations are documented.
10. It supports at least one North Star criterion.

## Not Sufficient

A feature is not complete merely because:

- a class exists;
- a database table exists;
- a UI tab exists;
- a mocked test passes;
- an agent can describe the feature;
- a percentage is displayed without evidence;
- a prompt asks the model to behave well.

## North Star Impact

Every phase report must include:

- teamwork impact;
- skills/knowledge quality impact;
- no-code management impact;
- trust impact;
- user-experience impact.

If a phase does not improve any criterion, the report must explain why it was necessary.

