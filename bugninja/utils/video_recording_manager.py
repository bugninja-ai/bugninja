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
import shutil
import time
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
        video_start_time (Optional[float]): UTC timestamp when video recording started (milliseconds)

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

    def __init__(self, run_id: str, config: VideoRecordingConfig, cli_mode: bool = False) -> None:
        """Initialize the video recording manager.

        Args:
            run_id (str): Unique identifier for the current run
            config (VideoRecordingConfig): Video recording configuration
            cli_mode (bool): Whether running in CLI mode (prevents automatic directory creation)
        """
        self.recorder = BugninjaVideoRecorder(config)
        self.run_id = run_id
        self.is_recording = False
        self.cdp_session: Optional[CDPSession] = None
        self.output_dir = config.output_dir
        self.cli_mode = cli_mode
        self.video_start_time: Optional[float] = None

        self.config = config

        # Only create directory if not in CLI mode
        if not self.cli_mode:
            Path(config.output_dir).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def check_ffmpeg_availability() -> bool:
        """Check if FFmpeg is available on the system.

        Returns:
            bool: True if FFmpeg is available, False otherwise
        """
        return shutil.which("ffmpeg") is not None

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
        # Check FFmpeg availability
        if not self.check_ffmpeg_availability():
            raise RuntimeError(
                "FFmpeg is not available on this system. Please install FFmpeg to enable video recording."
            )

        # Ensure output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Create full output path - use simple {run_id}.mp4 format for CLI mode
        if self.cli_mode:
            output_path = os.path.join(
                self.output_dir, f"{self.run_id}.{self.recorder.config.output_format}"
            )
        else:
            output_path = os.path.join(
                self.output_dir, f"run_{self.run_id}.{self.recorder.config.output_format}"
            )

        # Start recording
        await self.recorder.start_recording(output_path)
        self.cdp_session = cdp_session
        self.is_recording = True

        # Capture video start time for timestamp calculations
        self.video_start_time = time.time() * 1000  # UTC timestamp in milliseconds

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

    def get_video_offset(self, timestamp: float) -> Optional[float]:
        """Calculate video offset for a given timestamp.

        Args:
            timestamp (float): UTC timestamp in milliseconds

        Returns:
            Optional[float]: Video offset in seconds, or None if video not started

        Example:
            ```python
            offset = video_manager.get_video_offset(action_timestamp)
            if offset is not None:
                print(f"Action occurred at {offset:.2f}s into video")
            ```
        """
        if self.video_start_time is None:
            return None

        return (timestamp - self.video_start_time) / 1000.0  # Convert to seconds
