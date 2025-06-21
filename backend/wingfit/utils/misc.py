import base64
from uuid import uuid4

import requests
from fastapi import HTTPException

from .. import __version__


def generate_api_token() -> str:
    return str(uuid4())


def b64e(data: bytes) -> bytes:
    return base64.b64encode(data)


def b64img_decode(data: str) -> bytes:
    return (
        base64.b64decode(data.split(",", 1)[1]) if data.startswith("data:image/") else base64.b64decode(data)
    )


def check_update():
    url = "https://api.github.com/repos/itskovacs/wingfit/releases/latest"
    try:
        response = requests.get(url)
        response.raise_for_status()

        latest_version = response.json()["tag_name"]
        if __version__ != latest_version:
            return latest_version

        return None

    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail="Couldn't verify for update")
