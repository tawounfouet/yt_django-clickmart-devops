"""
Video processors (ffmpeg-python).

Install: pip install ffmpeg-python
System: apt install ffmpeg
Usage:
    from .processors import extract_thumbnail, extract_metadata, transcode
"""


def extract_metadata(file_path):
    """Extract duration, width, height, fps, codec."""
    raise NotImplementedError("Install ffmpeg-python: pip install ffmpeg-python")


def extract_thumbnail(file_path, output_path, time_offset=5):
    """Extract a frame as thumbnail at given time offset."""
    raise NotImplementedError("Install ffmpeg-python: pip install ffmpeg-python")


def transcode(file_path, output_path, codec='libx264', crf=23):
    """Transcode video to H.264."""
    raise NotImplementedError("Install ffmpeg-python: pip install ffmpeg-python")
