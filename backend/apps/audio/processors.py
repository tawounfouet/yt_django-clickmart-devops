"""
Audio processors (pydub, librosa).

Install: pip install pydub
Usage:
    from .processors import extract_metadata, transcode
"""


def extract_metadata(file_path):
    """Extract duration, sample_rate, bitrate, channels from audio file."""
    raise NotImplementedError("Install pydub: pip install pydub")


def transcode(file_path, target_format='mp3', bitrate='192k'):
    """Convert audio to target format."""
    raise NotImplementedError("Install pydub: pip install pydub")


def generate_waveform(file_path, output_path):
    """Generate waveform PNG from audio."""
    raise NotImplementedError("Install pydub: pip install pydub")
