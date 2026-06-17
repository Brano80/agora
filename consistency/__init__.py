"""The consistency gate — the most important safeguard in AGORA.

A v0 prototype died from an unspotted stock-flow leak. This package makes that
class of bug impossible to ship: it checks every period's transaction-flow and
balance-sheet matrices for the hard accounting laws and BLOCKS a run if the
books don't close.
"""
from consistency.checks import (
    CheckResult,
    ConsistencyReport,
    check_period,
    check_run,
    ConsistencyError,
    check_distribution,
    check_input_output,
)

__all__ = [
    "CheckResult",
    "ConsistencyReport",
    "check_period",
    "check_run",
    "ConsistencyError",
    "check_distribution",
    "check_input_output",
]
