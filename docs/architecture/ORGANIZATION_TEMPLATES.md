# Organization Templates

An `OrganizationTemplate` is a reusable, versioned proposal for an organization.
It contains purpose, recommended team size, member profession/position records,
an optional workflow, rationale and limitations.

Template lifecycle:

```text
create -> inspect -> owner approves -> instantiate -> assign agents/tools
       -> run work -> review -> revise template
```

U1 ships two data fixtures: `SOFTWARE_PRODUCT_TEAM` and
`CULINARY_PRODUCT_TEAM`. They use the same tables and service as user-created
templates. A fixture is a demonstration of genericity, not a promise that its
team composition is universally correct.

The expanded catalog composes a management model, responsibility model, domain
package, workflow, quality/review flags and team-size variant. Activation is a
wizard: identity and size, employee/provider assignment, workflow preview and
confirmation. The result is a real organization workspace with employees,
departments and routing metadata, not only role rows.
