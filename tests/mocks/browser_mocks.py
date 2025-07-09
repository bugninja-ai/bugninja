from unittest.mock import AsyncMock, MagicMock

from browser_use.browser.views import BrowserStateSummary


class MockPage:
    """Mock Playwright Page object"""

    def __init__(self, html_content: str = "<html><body>Test</body></html>"):
        self.html_content = html_content
        self.wait_for_load_state = AsyncMock()
        self.content = AsyncMock(return_value=html_content)

    async def get_content(self) -> str:
        return self.html_content


class MockBrowserSession:
    """Mock browser session for testing"""

    def __init__(self):
        self.current_page = MockPage()
        self.browser = MagicMock()
        self.playwright = MagicMock()
        self.selector_map = {}

    async def get_current_page(self) -> MockPage:
        return self.current_page

    async def get_state_summary(
        self, cache_clickable_elements_hashes: bool = True
    ) -> BrowserStateSummary:
        return BrowserStateSummary(
            url="https://example.com",
            title="Test Page",
            selector_map=self.selector_map,
            # ... other required fields
        )

    async def remove_highlights(self) -> None:
        pass

    async def close(self) -> None:
        pass
