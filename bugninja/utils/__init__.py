"""
Utility functions and classes for Bugninja framework.

This module provides **utility functions and classes** for:
- Logging configuration and setup
- Screenshot management and capture
- Selector generation and validation
- Prompt string factories

## Key Components

1. **ScreenshotManager** - Screenshot capture with element highlighting
2. **SelectorFactory** - XPath selector generation and validation
3. **set_logger_config** - Logging configuration utility
4. **prompt_string_factories** - Prompt generation utilities

## Usage Examples

```python
from bugninja.utils import ScreenshotManager, SelectorFactory

# Create screenshot manager
screenshot_manager = ScreenshotManager(folder_prefix="traversal")

# Take screenshot with highlighting
filename = await screenshot_manager.take_screenshot(
    page, action, browser_session
)

# Generate selectors
factory = SelectorFactory(html_content)
selectors = factory.generate_relative_xpaths_from_full_xpath("/html/body/button")
```
"""

from .screenshot_manager import ScreenshotManager
from .selector_factory import SelectorFactory

__all__ = ["ScreenshotManager", "SelectorFactory"]
