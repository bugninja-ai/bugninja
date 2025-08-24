import asyncio
import time
from typing import Optional

import numpy as np

from bugninja.config.video_recording import VideoRecordingConfig


class BugninjaVideoRecorder:
    """High-quality video recorder for Chromium browser using Playwright CDP and FFmpeg."""

    def __init__(self, config: VideoRecordingConfig) -> None:
        self.config = config
        self.frame_interval: float = 1.0 / config.fps
        self.ffmpeg_proc: Optional[asyncio.subprocess.Process] = None
        self.is_recording: bool = False
        self.frame_queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=config.max_queue_size)
        self.last_frame_time: float = 0.0
        self.frames_processed: int = 0
        self.last_frame_data: Optional[bytes] = None

    async def start_recording(self, output_file: str) -> None:
        """Start the recording process."""
        # Ensure output file has correct extension
        if not output_file.endswith(f".{self.config.output_format}"):
            output_file = f"{output_file}.{self.config.output_format}"

        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-s",
            f"{self.config.width}x{self.config.height}",
            "-r",
            str(self.config.fps),
            "-i",
            "pipe:0",
        ]

        # Add video encoding settings
        ffmpeg_cmd.extend(
            [
                "-c:v",
                self.config.codec,
                "-pix_fmt",
                self.config.pixel_format,
                "-preset",
                self.config.preset,
                "-crf",
                str(self.config.crf),
                "-b:v",
                self.config.bitrate,
                "-profile:v",
                "high",
            ]
        )

        # Add output file
        ffmpeg_cmd.append(output_file)

        self.ffmpeg_proc = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )

        self.is_recording = True
        self.frames_processed = 0
        asyncio.create_task(self._process_frames())

    async def stop_recording(self) -> dict[str, int]:
        """Stop the recording process."""
        self.is_recording = False

        if self.ffmpeg_proc:
            if self.ffmpeg_proc.stdin:
                self.ffmpeg_proc.stdin.close()
                await self.ffmpeg_proc.stdin.wait_closed()
            await self.ffmpeg_proc.wait()
            self.ffmpeg_proc = None

        return {"frames_processed": self.frames_processed}

    async def add_frame(self, frame_data: bytes) -> None:
        """Add a frame to the processing queue."""
        if self.is_recording:
            self.last_frame_data = frame_data
            try:
                self.frame_queue.put_nowait(frame_data)
            except asyncio.QueueFull:
                pass

    async def _process_frames(self) -> None:
        """Process frames from the queue at the target frame rate."""
        while self.is_recording or not self.frame_queue.empty():
            current_time: float = time.time()

            if current_time - self.last_frame_time >= self.frame_interval:
                frame_to_send: Optional[bytes] = None

                try:
                    frame_to_send = self.frame_queue.get_nowait()
                except asyncio.QueueEmpty:
                    if self.last_frame_data is not None:
                        frame_to_send = self.last_frame_data
                    else:
                        black_frame: np.ndarray = np.zeros(  # type: ignore
                            (self.config.height, self.config.width, 3), dtype=np.uint8
                        )
                        frame_to_send = black_frame.tobytes()

                if frame_to_send and (
                    self.ffmpeg_proc
                    and self.ffmpeg_proc.stdin
                    and not self.ffmpeg_proc.stdin.is_closing()
                ):
                    try:
                        self.ffmpeg_proc.stdin.write(frame_to_send)
                        await self.ffmpeg_proc.stdin.drain()
                        self.frames_processed += 1
                        self.last_frame_time = current_time
                    except Exception:
                        break

            await asyncio.sleep(0.001)
