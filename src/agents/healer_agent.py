from typing import Any, Dict, List

from browser_use.agent.service import logger  # type: ignore
from browser_use.agent.views import AgentBrain  # type: ignore

from src.agents.custom_controller import BugninjaController
from src.agents.navigator_agent import NavigatorAgent


#! keep in mind that the HealerAgent is not inherited from BugninjaAgentBase but from the NavigatorAgent directly
#! for this reason it inherits the NavigatorAgent hooks as well
class HealerAgent(NavigatorAgent):

    async def _before_run_hook(self) -> None:
        logger.info(msg="🏁 BEFORE-Run hook called")

        self.agent_taken_actions: List[Dict[str, Any]] = []
        self.agent_brain_states: Dict[str, AgentBrain] = {}

        #! we override the default controller with our own
        self.controller = BugninjaController()

    #! right now we do not want to save the agent actions
    async def _after_run_hook(self) -> None: ...
