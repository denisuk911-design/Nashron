# Architecture Decisions

All architecture decisions must support `docs/product/PRODUCT_NORTH_STAR.md`.

Permanent product goals:
- employees actually work as a team;
- skills and knowledge measurably improve work quality;
- the owner manages the system without editing code.

## ADR-001: Routing Is Deterministic

Prompt text alone is not allowed to decide who answers. `TeamRouter` selects responders before provider invocation.

## ADR-002: Silence Is Valid

Broadcast and non-addressed employees may produce no answer. Silence is not an error.

## ADR-003: No Impersonation

If one provider writes messages for another employee, foreign speaker parts are not accepted as real messages.

## ADR-004: Evidence Controls Skill Progress

Skill progress is not based on self-reported learning. It is derived from skill usage, runs, artifacts and review evidence.

## ADR-005: Product Metrics Are Local And Evidence-Based

Roman 2050 optimizes for routing accuracy, evidence-backed completion, fewer repeated findings and owner control. Message count and agent activity are not success metrics.

## ADR-006: Provider Is Infrastructure

Employee identity, role, skills, permissions and work history must stay separate from the CLI provider. A future provider change must not erase the employee.
