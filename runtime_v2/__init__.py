"""Experimental Team2050 Runtime V2.

This package is deliberately isolated from the production chat runtime.  It
contains framework-neutral contracts and a local prototype used by tests and
architecture benchmarks.
"""

from .engine import PrototypeWorkflowEngine
from .intent_gate import WorkIntentGate
from .models import WorkIntent, WorkflowStatus

__all__ = ["PrototypeWorkflowEngine", "WorkIntent", "WorkIntentGate", "WorkflowStatus"]
