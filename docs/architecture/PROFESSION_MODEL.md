# Profession Model

`Profession` describes a reusable professional capability package. It contains
responsibilities, expected results, capabilities, initial skills, recommended
tools, knowledge sources and a qualification method.

It is different from:

- `Role`: responsibility in a particular workflow or organization.
- `Position`: the human-readable seat in an organization.
- `Skill`: a versioned ability that can be practiced and evidenced.
- `Agent`: the employee identity that performs the work.

Profession records are data, not Python classes. An owner can create an
arbitrary profession from the Organization tab and use it in a template.
Domain packages may provide defaults, but they do not change the core model.
