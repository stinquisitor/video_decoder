from tempfile import NamedTemporaryFile

import os
from fastapi import HTTPException


AUDIO_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".awb",
    ".aac",
    ".ogg",
    ".oga",
    ".m4a",
    ".wma",
    ".amr",
}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".wmv", ".mkv"}
ALLOWED_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS


def validate_extension(filename, allowed_extensions: dict):
    """
    Check the file extension of the given file and compare it if its is in the allowed AUDIO and VIDEO.

    Args:
        file (str): The path to the file.

    """
    file_extension = os.path.splitext(filename)[1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file extension: {file_extension}. Allowed: {allowed_extensions}",
        )


def check_file_extension(file):
    """
    Check the file extension of the given file and compare it if its is in the allowed AUDIO and VIDEO.

    Args:
        file (str): The path to the file.

    """
    validate_extension(file, ALLOWED_EXTENSIONS)

