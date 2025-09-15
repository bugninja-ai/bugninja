"""
Video recording management utilities for Bugninja framework.

This module provides video recording management functionality for browser automation
sessions, including session lifecycle management, frame capture coordination, and
integration with the custom video recorder for high-quality video output.

## Key Components

1. **VideoRecordingManager** - Main class for video recording session management
2. **CDP Integration** - Chrome DevTools Protocol integration for frame capture
3. **Session Lifecycle** - Start/stop recording with proper cleanup
4. **Frame Management** - Coordinated frame addition and processing

## Usage Examples

```python
from bugninja.utils import VideoRecordingManager
from bugninja.config.video_recording import VideoRecordingConfig

# Create video recording manager
config = VideoRecordingConfig()
video_manager = VideoRecordingManager("test_run", config)

# Start recording
await video_manager.start_recording("output", cdp_session)

# Add frames during recording
await video_manager.add_frame(frame_data)

# Stop recording
stats = await video_manager.stop_recording()
```
"""

import os
from pathlib import Path
from typing import Optional

from playwright.async_api import CDPSession

from bugninja.config.video_recording import VideoRecordingConfig
from bugninja.utils.custom_video_recorder import BugninjaVideoRecorder


class VideoRecordingManager:
    """Manager for video recording functionality in Bugninja agents.

    This class provides comprehensive video recording management for browser automation
    sessions, including session lifecycle management, frame capture coordination, and
    integration with the custom video recorder for high-quality video output.

    Attributes:
        recorder (BugninjaVideoRecorder): Custom video recorder instance
        run_id (str): Unique identifier for the current run
        is_recording (bool): Whether recording is currently active
        cdp_session (Optional[CDPSession]): Chrome DevTools Protocol session
        output_dir (str): Directory for output video files
        config (VideoRecordingConfig): Video recording configuration

    Example:
        ```python
        from bugninja.utils import VideoRecordingManager
        from bugninja.config.video_recording import VideoRecordingConfig

        # Create video recording manager
        config = VideoRecordingConfig()
        video_manager = VideoRecordingManager("test_run", config)

        # Start recording
        await video_manager.start_recording("output", cdp_session)

        # Add frames during recording
        await video_manager.add_frame(frame_data)

        # Stop recording
        stats = await video_manager.stop_recording()
        ```
    """

    def __init__(self, run_id: str, config: VideoRecordingConfig) -> None:
        """Initialize the video recording manager.

        Args:
            run_id (str): Unique identifier for the current run
            config (VideoRecordingConfig): Video recording configuration
        """
        self.recorder = BugninjaVideoRecorder(config)
        self.run_id = run_id
        self.is_recording = False
        self.cdp_session: Optional[CDPSession] = None
        self.output_dir = config.output_dir

        self.config = config

        Path(config.output_dir).mkdir(parents=True, exist_ok=True)

    async def start_recording(self, output_file: str, cdp_session: CDPSession) -> None:
        """Start video recording.

        Args:
            output_file (str): Base name for the output file
            cdp_session (CDPSession): CDP session for frame capture

        Example:
            ```python
            await video_manager.start_recording("session_recording", cdp_session)
            ```
        """
        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Create full output path
        output_path = os.path.join(
            self.output_dir, f"run_{self.run_id}.{self.recorder.config.output_format}"
        )

        # Start recording
        await self.recorder.start_recording(output_path)
        self.cdp_session = cdp_session
        self.is_recording = True

    async def stop_recording(self) -> dict[str, int]:
        """Stop video recording.

        Returns:
            dict[str, int]: Recording statistics including frames processed

        Example:
            ```python
            stats = await video_manager.stop_recording()
            print(f"Processed {stats['frames_processed']} frames")
            ```
        """
        if self.is_recording:
            stats = await self.recorder.stop_recording()
            self.is_recording = False
            return stats
        return {"frames_processed": 0}

    async def add_frame(self, frame_data: bytes) -> None:
        """Add a frame to the recording.

        Args:
            frame_data (bytes): Raw frame data in bytes

        Example:
            ```python
            await video_manager.add_frame(frame_bytes)
            ```
        """
        if self.is_recording:
            await self.recorder.add_frame(frame_data)
