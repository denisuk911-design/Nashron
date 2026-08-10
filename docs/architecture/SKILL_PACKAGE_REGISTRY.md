# Skill Package Registry

Skill packages are owner-managed records. They are separate from employee skill
progress and from chat-generated working notes.

Implemented entities:

- `skill_packages`: stable skill package identity, purpose, role support,
  instructions, validation checklist, qualification tasks, version and status.
- `skill_package_events`: append-only package audit events.
- `employee_skill_assignments`: explicit employee-to-skill state.

Package statuses:

- `DRAFT`
- `READY_FOR_REVIEW`
- `ACTIVE`
- `SUSPENDED`
- `DEPRECATED`
- `REJECTED`

Employee skill states:

- `ASSIGNED`
- `STUDYING`
- `PRACTICED`
- `DEMONSTRATED`
- `REVIEWED`
- `QUALIFIED`
- `REQUIRES_RETRAINING`
- `EXPIRED`

Director Console behavior:

- the owner can create a draft skill package;
- the owner can activate or suspend a package;
- the owner can assign a package to an employee;
- assigned packages appear in skill progress;
- assignment alone gives `0%` evidence progress.

Evidence rules:

- a package record does not qualify an employee;
- an assignment does not qualify an employee;
- chat claims do not qualify an employee;
- progress increases only through successful runs, file evidence and independent
  review evidence counted by `SkillProgressService`.

Known limitations:

- package editing after creation is limited to status and assignment;
- import/export of full `SKILL.md` packages is future work;
- owner approval flow is represented by status changes, not a dedicated approval
  wizard yet.
