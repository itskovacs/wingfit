import base64
from uuid import uuid4

import httpx
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


async def httpx_get(link: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": link,
    }

    try:
        async with httpx.AsyncClient(follow_redirects=True, headers=headers, timeout=5) as client:
            response = await client.get(link)
            response.raise_for_status()
            return response.json()
    except Exception:
        raise HTTPException(status_code=400, detail=f"Error while fetching {link}")


async def check_update():
    url = "https://api.github.com/repos/itskovacs/wingfit/releases/latest"
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=5) as client:
            response = await client.get(url)
            response.raise_for_status()

        latest_version = response.json()["tag_name"]
        if __version__ != latest_version:
            return latest_version

        return None

    except Exception:
        raise HTTPException(status_code=503, detail="Couldn't verify for update")
