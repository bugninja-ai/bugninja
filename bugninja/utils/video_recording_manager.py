import os
from pathlib import Path
from typing import Optional

from playwright.async_api import CDPSession

from bugninja.config.video_recording import VideoRecordingConfig
from bugninja.utils.custom_video_recorder import BugninjaVideoRecorder


class VideoRecordingManager:
    """Manager for video recording functionality in Bugninja agents."""

    def __init__(self, run_id: str, config: VideoRecordingConfig) -> None:
        """Initialize the video recording manager.

        Args:
            run_id: Unique identifier for the current run
            config: Video recording configuration
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
            output_file: Base name for the output file
            cdp_session: CDP session for frame capture
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
            dict: Recording statistics
        """
        if self.is_recording:
            stats = await self.recorder.stop_recording()
            self.is_recording = False
            return stats
        return {"frames_processed": 0}

    async def add_frame(self, frame_data: bytes) -> None:
        """Add a frame to the recording.

        Args:
            frame_data: Raw frame data in bytes
        """
        if self.is_recording:
            await self.recorder.add_frame(frame_data)
