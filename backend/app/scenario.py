"""Deterministic failure-injection modes for the simulator (docs/MVP_SCOPE.md
§ Milestone 2, spec §12). A single source of truth for the four mode names,
shared by the Task model, the simulator's request schemas, the agent's
tool-execution harness, and the evidence adapter.

The agent itself never sees scenario_mode — it is stamped onto simulator
requests by the harness (app/agent.py, app/adapter.py), the same way run_id
is, not something the LLM reasons about or can influence.
"""

from typing import Literal

NORMAL = "NORMAL"
FALSE_ACK = "FALSE_ACK"
DROP_NOTIFICATION = "DROP_NOTIFICATION"
READ_UNAVAILABLE = "READ_UNAVAILABLE"

SCENARIO_MODES = (NORMAL, FALSE_ACK, DROP_NOTIFICATION, READ_UNAVAILABLE)

ScenarioMode = Literal["NORMAL", "FALSE_ACK", "DROP_NOTIFICATION", "READ_UNAVAILABLE"]
