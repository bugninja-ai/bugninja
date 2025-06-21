from typing import Literal

from browser_use import BrowserSession  # type: ignore
from browser_use.agent.views import ActionResult  # type: ignore
from browser_use.controller.service import Controller, logger  # type: ignore
from browser_use.controller.views import ScrollAction  # type: ignore
from pydantic import BaseModel


class BugninjaController(Controller):

    def __init__(
        self,
        exclude_actions: list[str] = [],
        output_model: type[BaseModel] | None = None,
        verbose: bool = False,
    ):
        super().__init__(exclude_actions=exclude_actions, output_model=output_model)
        self.verbose = verbose

        async def handle_scroll(
            scroll_action: ScrollAction,
            browser_session: BrowserSession,
            type: Literal["up", "down"],
        ) -> ActionResult:
            page = await browser_session.get_current_page()
            page_height = await page.evaluate("() => window.innerHeight")
            dy = scroll_action.amount or page_height

            if type == "up":
                dy = -dy

            await page.wait_for_load_state("load")

            # ? version#1
            # container_scrolling_success = await self._scroll_container(page, dy)

            # ? version#2
            # await page.evaluate("(y) => window.scrollBy(0, y)", dy)

            # ? version#3
            await page.mouse.wheel(delta_x=0, delta_y=dy)

            msg = f"🔍 Scrolled down the page by {dy} pixels"

            logger.info(msg)
            return ActionResult(extracted_content=msg, include_in_memory=True)

        @self.registry.action(
            "Scroll down the page by pixel amount - if none is given, scroll one page",
            param_model=ScrollAction,
        )
        async def scroll_down(
            params: ScrollAction, browser_session: BrowserSession
        ) -> ActionResult:
            return await handle_scroll(params, browser_session, "down")

        @self.registry.action(
            "Scroll up the page by pixel amount - if none is given, scroll one page",
            param_model=ScrollAction,
        )
        async def scroll_up(params: ScrollAction, browser_session: BrowserSession) -> ActionResult:
            return await handle_scroll(params, browser_session, "up")
