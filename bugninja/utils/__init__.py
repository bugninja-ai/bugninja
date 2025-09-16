"""
Utility functions and classes for Bugninja framework.

This module provides **utility functions and classes** for:
- Logging configuration and setup
- Screenshot management and capture
- Selector generation and validation
- Video recording and management
- Custom video recording with FFmpeg

## Key Components

1. **ScreenshotManager** - Screenshot capture with element highlighting
2. **SelectorFactory** - XPath selector generation and validation
3. **VideoRecordingManager** - Video recording management for browser sessions
4. **BugninjaVideoRecorder** - High-quality video recorder using FFmpeg
5. **BugninjaLogger** - Custom logging with Bugninja-specific levels
6. **configure_logging()** - Logging configuration utility

## Usage Examples

```python
from bugninja.utils import (
    ScreenshotManager,
    SelectorFactory,
    VideoRecordingManager,
    BugninjaVideoRecorder,
    logger
)
from bugninja.config.video_recording import VideoRecordingConfig

# Create screenshot manager
screenshot_manager = ScreenshotManager(run_id="test_run")

# Take screenshot with highlighting
filename = await screenshot_manager.take_screenshot(
    page, action, browser_session
)

# Generate selectors
factory = SelectorFactory(html_content)
selectors = factory.generate_relative_xpaths_from_full_xpath("/html/body/button")

# Create video recording manager
config = VideoRecordingConfig()
video_manager = VideoRecordingManager("test_run", config)

# Use custom logging
logger.bugninja_log("Custom log message")
```
"""

from .screenshot_manager import ScreenshotManager
from .selector_factory import SelectorFactory
from .video_recording_manager import VideoRecordingManager
from .custom_video_recorder import BugninjaVideoRecorder
from .logging_config import logger, configure_logging, BugninjaLogger

__all__ = [
    "ScreenshotManager",
    "SelectorFactory",
    "VideoRecordingManager",
    "BugninjaVideoRecorder",
    "logger",
    "configure_logging",
    "BugninjaLogger",
]
