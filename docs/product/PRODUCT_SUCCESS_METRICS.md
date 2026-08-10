# Product Success Metrics

Source of truth: `docs/product/PRODUCT_NORTH_STAR.md`.

Roman 2050 must be measured by useful work, trust and controllability, not by message volume.

Current implementation exposes a compact local diagnostics view in `Команда -> Диагностика`.

## Team Behavior

- Direct-address routing accuracy.
- Direct-address delivery rate from saved `explicit_recipients` and `selected_responders`.
- Unnecessary responder rate.
- Duplicate-response rate.
- Open owner-question count.
- Successful handoff rate.
- Handoff delivery from saved `contextual_handoff_scheduled` and `contextual_handoff_started` events.
- Unresolved loop count.
- Context-consistency rate.

Target direction:
- direct messages invoke only the intended employee;
- non-addressed employees stay silent unless a critical interruption is justified;
- handoffs create clear owner, reviewer and next-step state.
- handoffs name an active employee and are not guessed from generic review wording alone.
- handoff success is counted when the target employee run actually starts, not when another employee merely promises to pass work over.
- owner questions stay open until an assigned employee answer is stored, then wait for owner acceptance or return to work.

## Trust

- Unsupported claim rate.
- Evidence-backed completion rate.
- False-success rate.
- Cancelled or interrupted runs incorrectly marked successful.
- Impersonation attempts rejected.

Target direction:
- important claims have task/run/file/source evidence;
- unsupported claims do not update task, skill, finding or knowledge state.

## Quality

- Findings per task.
- Repeated finding rate.
- Rework cycles.
- Qualification pass rate.
- Standards compliance.
- Artifact completeness.
- Reproducibility of checks.

Target direction:
- skills and knowledge must reduce repeat failures and rework over time.

## Usability

- Time to first visible status.
- Time to useful result.
- Cancellation success.
- Tasks completed without editing configuration files.
- Management actions completed through GUI.

Target direction:
- the owner manages employees, providers, permissions, skills and knowledge from the app.

## Learning

- Skills assigned.
- Skills practiced.
- Skills demonstrated.
- Skills reviewed.
- Skills qualified.
- Knowledge cards actually used, counted from `APPLIED` usage events rather than
  prompt supply alone.
- Standards actually used, counted from `APPLIED` usage events rather than
  prompt supply alone.
- Measurable quality change after training.

Target direction:
- learning is evidence-based and review-controlled;
- self-reported learning is never enough;
- `SUPPLIED`, `APPLIED`, `IGNORED` and `MISAPPLIED` are tracked separately for
  knowledge and standard cards.
