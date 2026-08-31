from __future__ import annotations

from .models import Action, ActionType


class AutonomyPolicy:
    """Local workspace work is autonomous; external and commercial actions are not."""

    EXTERNAL_ACTIONS = {ActionType.MCP_CALL, ActionType.BROWSER_CALL}
    RISK_TOKENS = ("publish", "publication", "deploy", "purchase", "payment", "money", "transfer", "оплат", "куп", "публикац")

    @classmethod
    def requires_owner_approval(cls, action: Action) -> bool:
        if action.action_type in cls.EXTERNAL_ACTIONS:
            return True
        # File contents are work output, not an instruction to publish or pay for
        # anything.  Inspect only routing/target fields when deciding HITL risk.
        risk_fields = ("path", "source", "destination", "command", "adapter_id", "tool_name")
        payload = " ".join(str(action.payload.get(field, "")) for field in risk_fields).lower()
        return any(token in payload for token in cls.RISK_TOKENS)
