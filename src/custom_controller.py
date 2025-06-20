from typing import Dict, Literal

from browser_use import BrowserSession  # type: ignore
from browser_use.agent.views import ActionResult  # type: ignore
from browser_use.controller.service import Controller, logger, Page  # type: ignore
from browser_use.controller.views import ScrollAction  # type: ignore
from pydantic import BaseModel
from rich import print as rich_print


class BugninjaController(Controller):

    # ? This function is left here only for reference reasons. It is the corrected version of the original function implemented by browser-use
    # ? might come in handy if the raw wheel scrolling doesn't work
    async def _scroll_container(self, page: Page, pixels: int) -> None:
        """Scroll the element that truly owns vertical scroll. Prioritizes the main content area over sidebars and fixed elements."""
        SMART_SCROLL_JS = """(dy) => {
            try {
                const logElementInfo = (el, prefix) => {
                    if (!el) return 'null';
                    const style = getComputedStyle(el);
                    return {
                        tagName: el.tagName,
                        id: el.id,
                        className: el.className,
                        overflowY: style.overflowY,
                        clientHeight: el.clientHeight,
                        scrollHeight: el.scrollHeight,
                        windowHeight: window.innerHeight,
                        isBigEnough: el.clientHeight >= window.innerHeight * 0.5,
                        canScroll: /(auto|scroll|overlay)/.test(style.overflowY) && 
                                 el.scrollHeight > el.clientHeight && 
                                 el.clientHeight >= window.innerHeight * 0.5,
                        position: style.position,
                        width: el.clientWidth,
                        isMainContent: el.clientWidth >= window.innerWidth * 0.6 // Main content is usually wider
                    };
                };

                // Helper function to check if element is likely a sidebar or fixed element
                const isSidebarOrFixed = (el) => {
                    if (!el) return false;
                    const style = getComputedStyle(el);
                    const isFixed = style.position === 'fixed' || style.position === 'sticky';
                    const isNarrow = el.clientWidth < window.innerWidth * 0.4;
                    const hasSidebarClass = el.className.toLowerCase().includes('sidebar');
                    return isFixed || isNarrow || hasSidebarClass;
                };

                // Helper function to check if element is likely main content
                const isMainContent = (el) => {
                    if (!el) return false;
                    const style = getComputedStyle(el);
                    const isWide = el.clientWidth >= window.innerWidth * 0.6;
                    const isScrollable = /(auto|scroll|overlay)/.test(style.overflowY) && 
                                       el.scrollHeight > el.clientHeight;
                    return isWide && isScrollable;
                };

                const bigEnough = el => el.clientHeight >= window.innerHeight * 0.5;
                const canScroll = el =>
                    el &&
                    /(auto|scroll|overlay)/.test(getComputedStyle(el).overflowY) &&
                    el.scrollHeight > el.clientHeight &&
                    bigEnough(el);

                // First try to find the main content area
                let mainContent = [...document.querySelectorAll('*')].find(isMainContent);
                console.log('Main content element:', logElementInfo(mainContent, 'main'));

                // If no main content found, fall back to the original logic
                let el = mainContent || document.activeElement;
                console.log('Initial element:', logElementInfo(el, 'active'));

                // Traverse up until we find a suitable scrollable element
                let parentTraversal = [];
                while (el && !canScroll(el) && el !== document.body) {
                    if (!isSidebarOrFixed(el)) {
                        parentTraversal.push(logElementInfo(el, 'parent'));
                    }
                    el = el.parentElement;
                }
                console.log('Parent traversal:', parentTraversal);

                // Select final element, avoiding sidebars
                const finalElement = (canScroll(el) && !isSidebarOrFixed(el))
                    ? el
                    : [...document.querySelectorAll('*')]
                        .filter(el => canScroll(el) && !isSidebarOrFixed(el))
                        .find(el => isMainContent(el)) || document.scrollingElement;

                console.log('Final selected element:', logElementInfo(finalElement, 'final'));

                if (finalElement === document.scrollingElement ||
                    finalElement === document.documentElement ||
                    finalElement === document.body) {
                    console.log('Using window scroll');
                    window.scrollBy(0, dy);
                    return { 
                        success: true, 
                        message: 'Window scrolled successfully',
                        elementInfo: logElementInfo(finalElement, 'window')
                    };
                } else {
                    console.log('Using element scroll');
                    finalElement.scrollBy({ top: dy, behavior: 'auto' });
                    return { 
                        success: true, 
                        message: 'Element scrolled successfully',
                        elementInfo: logElementInfo(finalElement, 'element')
                    };
                }
            } catch (error) {
                return { 
                    success: false, 
                    error: error.message,
                    stack: error.stack,
                    type: error.name
                };
            }
        }"""
        await page.wait_for_load_state("load")
        result: Dict[str, str] = await page.evaluate(SMART_SCROLL_JS, pixels)

        success: bool = result.get("success", False)

        if not success:
            logger.error(f"JavaScript scroll error: {result.get('error')}")
            logger.error(f"Error type: {result.get('type')}")
            logger.error(f"Stack trace: {result.get('stack')}")

        if self.verbose:
            # Log the element information
            element_info = result.get("elementInfo", {})
            logger.info(f"Scroll successful: {result.get('message')}")
            logger.info(
                f"Element details: Tag={element_info.get('tagName')}, "
                f"ID={element_info.get('id')}, "
                f"Class={element_info.get('className')}"
            )
            logger.info(
                f"Scroll properties: overflowY={element_info.get('overflowY')}, "
                f"clientHeight={element_info.get('clientHeight')}, "
                f"scrollHeight={element_info.get('scrollHeight')}, "
                f"windowHeight={element_info.get('windowHeight')}"
            )
            logger.info(
                f"Scrollability: isBigEnough={element_info.get('isBigEnough')}, "
                f"canScroll={element_info.get('canScroll')}, "
                f"isMainContent={element_info.get('isMainContent')}"
            )

        return success

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

            # ? version#1
            # container_scrolling_success = await self._scroll_container(page, dy)

            # ? version#2
            # await page.evaluate("(y) => window.scrollBy(0, y)", dy)
            await page.wait_for_load_state("load")

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
