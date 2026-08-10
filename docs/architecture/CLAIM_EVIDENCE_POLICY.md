# Claim Evidence Policy

North Star reference: `docs/product/PRODUCT_NORTH_STAR.md`.

Employees may plan work freely, but completed claims require evidence.

Controlled claim outcomes:
- `CLAIM_SUPPORTED`;
- `CLAIM_PARTIALLY_SUPPORTED`;
- `CLAIM_UNSUPPORTED`;
- `CLAIM_CONTRADICTED`.

Unsupported phrases include statements such as `проверил`, `подтвердил`, `файл исправлен`, `ошибок нет`, `источник найден`, `навык освоен` when there is no structured evidence.

The raw provider response is preserved in `agent_runs.raw_response`. The user-facing chat may show a system warning, and unsupported claims do not update skills.

Validation lives in `core/claim_evidence.py`.
