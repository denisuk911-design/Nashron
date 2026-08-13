"""Framework-neutral Runtime V2 benchmark prototype.

This package is deliberately isolated from the production ``runtime_v2``
package. It exists to test architectural contracts before a migration decision.
"""

from .models import CanonicalAgentState, StructuredHandoff, Task
from .prototype import AgentRuntimePrototype, ProviderAdapter
from .store import SQLitePrototypeStore

__all__ = [
    "AgentRuntimePrototype",
    "CanonicalAgentState",
    "ProviderAdapter",
    "SQLitePrototypeStore",
    "StructuredHandoff",
    "Task",
]
