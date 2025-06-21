from io import BytesIO
from pathlib import Path
from uuid import uuid4

import aiofiles
import httpx
from fastapi import HTTPException, UploadFile
from PIL import Image

from ..config import settings
from ..utils.logging import app_logger


def generate_filename(format: str) -> str:
    return f"{uuid4()}.{format}"


def assets_folder_path() -> Path:
    return Path(settings.ASSETS_FOLDER)


def remove_image(path: str):
    try:
        Path(assets_folder_path() / path).unlink()
    except OSError as exc:
        raise Exception("Error deleting image:", exc, path)


async def read_image(filename: str) -> bytes:
    file_path = Path(settings.ASSETS_FOLDER) / filename
    # TODO: Chunk yield
    async with aiofiles.open(file_path, "rb") as f:
        return await f.read()


async def upload_f_to_tempfile(upload_file: UploadFile) -> str:
    try:
        async with aiofiles.tempfile.NamedTemporaryFile("wb", delete=False) as tmpfile:
            while chunk := await upload_file.read(1024 * 1024):
                await tmpfile.write(chunk)
            return tmpfile.name
    except Exception as exc:
        app_logger.error(f"[upload_f_to_tempfile] Exception: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Roses are red, violets are blue, if you're reading this, I'm sorry for you",
        )


async def download_file(link: str) -> str:
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=8) as client:
            response = await client.get(link)
            response.raise_for_status()

            async with aiofiles.tempfile.NamedTemporaryFile("wb", delete=False) as tmpfile:
                await tmpfile.write(response.content)
                return tmpfile.name
    except httpx.HTTPStatusError as exc:
        app_logger.error(f"[download_file] Failed to download file: {exc}")
        raise HTTPException(status_code=400, detail="Failed to download file")
    except Exception as exc:
        app_logger.error(f"[download_file] Exception: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Roses are red, violets are blue, if you're reading this, I'm sorry for you",
        )


def save_image(content: bytes, size: int = 128) -> str:
    try:
        with Image.open(BytesIO(content)) as im:
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGB")

            if size > 0:  # Crop as square of (size * size)
                im_ratio = im.width / im.height
                target_ratio = 1  # Square ratio is 1

                if im_ratio > target_ratio:
                    new_height = size
                    new_width = int(new_height * im_ratio)
                else:
                    new_width = size
                    new_height = int(new_width / im_ratio)

                im = im.resize((new_width, new_height), Image.LANCZOS)

                left = (im.width - size) // 2
                top = (im.height - size) // 2
                right = left + size
                bottom = top + size

                im = im.crop((left, top, right, bottom))

            if content.startswith(b"\x89PNG"):
                image_ext = "png"
            elif content.startswith(b"\xff\xd8"):
                image_ext = "jpeg"
            elif content.startswith(b"RIFF") and content[8:12] == b"WEBP":
                image_ext = "webp"
            else:
                raise ValueError("Unsupported image format")

            filename = generate_filename(image_ext)
            filepath = assets_folder_path() / filename
            im.save(filepath)

            return filename

    except Exception as exc:
        app_logger.error(f"[save_image] Exception: {exc}")
    return ""
