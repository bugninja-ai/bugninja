from typing import Awaitable, Callable

from browser_use.agent.service import Agent  # type: ignore

# -------------------

AgentHookFunc = Callable[["Agent"], Awaitable[None]]
