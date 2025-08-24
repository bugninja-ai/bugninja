from pydantic import BaseModel, Field


class VideoRecordingConfig(BaseModel):
    """Configuration for video recording functionality."""

    enabled: bool = Field(default=False, description="Enable video recording")
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
