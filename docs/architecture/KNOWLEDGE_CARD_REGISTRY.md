# Knowledge Card Registry

Knowledge cards are owner-controlled engineering knowledge records.

They are not employee chat memories and not unreviewed claims. A card becomes
usable by agents only when its status is `ACTIVE`.

Implemented entities:

- `knowledge_cards`: title, summary, content, source metadata, role scope, tags,
  status, version and review notes.
- `knowledge_card_events`: append-only card audit events.
- `knowledge_usage`: existing Phase 1 table now records when an active card was
  supplied to an agent prompt and how the run later accounted for that card.

Knowledge states:

- `DRAFT`
- `NEEDS_SOURCE_RECHECK`
- `NEEDS_REVIEW`
- `ACTIVE`
- `CONFLICTING`
- `REJECTED`
- `SUPERSEDED`

Source authority vocabulary:

- `OFFICIAL`
- `PRIMARY`
- `STANDARD`
- `TEXTBOOK`
- `INTERNAL_VERIFIED`
- `COMMUNITY`
- `UNVERIFIED`

Director Console behavior:

- owner can add a draft card;
- owner can move a card to review, active or rejected;
- active cards are retrieved by deterministic keyword/role matching;
- prompt supply is recorded as `knowledge_usage` with `usage_type=SUPPLIED`;
- structured responses can record `APPLIED`, `IGNORED` or `MISAPPLIED` for
  cards that were supplied to the same run.

Trust rules:

- draft/rejected/conflicting cards are not supplied to agents;
- a card source authority is explicit;
- supplying a card does not prove it was correctly applied;
- application evidence is accepted only when the structured response references
  a card ID that was actually supplied to the same run;
- supplied cards that are not referenced in structured response are recorded as
  `IGNORED` for that run;
- invented card IDs are rejected and logged.

Known limitations:

- retrieval is keyword-based, not semantic;
- source hash is a field but file import/hash calculation is not automated yet;
- standards registry and approval workflow remain separate future work;
- `APPLIED` currently means the run explicitly accounted for the supplied card
  in structured evidence; deeper semantic verification remains future work;
- the GUI supports creation and status changes, not full editing/version
  comparison yet.
