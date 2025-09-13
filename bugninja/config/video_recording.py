"""
Video recording configuration for browser automation sessions.

This module provides configuration settings for video recording functionality
during browser automation sessions, including video quality, format, and
encoding parameters.
"""

from pydantic import BaseModel, Field


class VideoRecordingConfig(BaseModel):
    """Configuration for video recording functionality.

    This class provides comprehensive configuration options for recording
    browser automation sessions as video files, including quality settings,
    encoding parameters, and output specifications.

    Attributes:
        width (int): Video width in pixels (default: 1920)
        height (int): Video height in pixels (default: 1080)
        fps (int): Target frame rate (default: 60)
        quality (int): JPEG quality for screencast frames (default: 100)
        output_format (str): Output video format (default: "mp4")
        codec (str): Video codec for encoding (default: "libx264")
        preset (str): FFmpeg encoding preset (default: "slow")
        crf (int): Constant Rate Factor for quality control (default: 16)
        bitrate (str): Target bitrate for video encoding (default: "25M")
        pixel_format (str): Output pixel format (default: "yuv420p")
        max_queue_size (int): Maximum frame queue size (default: 200)
        output_dir (str): Directory for output video files (default: "./screen_recordings")

    Example:
        ```python
        from bugninja.config.video_recording import VideoRecordingConfig

        # Basic configuration
        config = VideoRecordingConfig()

        # Custom configuration
        config = VideoRecordingConfig(
            width=1280,
            height=720,
            fps=30,
            quality=80,
            output_format="webm"
        )
        ```
    """

    width: int = Field(default=1920, description="Video width in pixels")
    height: int = Field(default=1080, description="Video height in pixels")
    fps: int = Field(default=60, description="Target frame rate")
    quality: int = Field(default=100, description="JPEG quality for screencast")
    output_format: str = Field(default="mp4", description="Output video format")
    codec: str = Field(default="libx264", description="Video codec")
    preset: str = Field(default="slow", description="FFmpeg preset")
    crf: int = Field(default=16, description="Constant Rate Factor (quality)")
    bitrate: str = Field(default="25M", description="Target bitrate")
    pixel_format: str = Field(default="yuv420p", description="Output pixel format")
    max_queue_size: int = Field(default=200, description="Frame queue size")
    output_dir: str = Field(default="./screen_recordings", description="Output directory")
