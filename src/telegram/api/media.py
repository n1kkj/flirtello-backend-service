"""
Media handling functions for Telegram API.

This module provides functions for sending and managing media files (photos, videos, animations),
including caching of file_id to optimize repeated sends.
"""
import io
import json
import os
import re
import urllib.parse
from typing import Any, Optional, Union

import sentry_sdk

from .core import _request_with_fixed_retry, client, logger

# --- START: Simple local cache for Telegram file_id per media URL and bot token ---
_CACHE_PATH: Optional[str] = None
_MEDIA_CACHE: dict = {}


def _get_cache_path() -> str:
    global _CACHE_PATH
    if _CACHE_PATH is not None:
        return _CACHE_PATH
    cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "flirtello")
    try:
        os.makedirs(cache_dir, exist_ok=True)
    except Exception:
        # Fallback to current directory
        cache_dir = "."
    _CACHE_PATH = os.path.join(cache_dir, "tg_media_cache.json")
    return _CACHE_PATH


def _load_media_cache() -> dict:
    global _MEDIA_CACHE
    if _MEDIA_CACHE:
        return _MEDIA_CACHE
    path = _get_cache_path()
    try:
        with open(path, "r", encoding="utf-8") as f:
            _MEDIA_CACHE = json.load(f)
    except Exception:
        _MEDIA_CACHE = {}
    return _MEDIA_CACHE


def _save_media_cache(cache: dict) -> None:
    path = _get_cache_path()
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cache, f)
    except Exception:
        pass


def _cache_key(url: str, token: str) -> str:
    return f"{token[:12]}::{url}"


def get_cached_file_id(url: str, token: str) -> Optional[dict]:
    """Get cached file_id for a media URL."""
    cache = _load_media_cache()
    entry = cache.get(_cache_key(url, token))
    if isinstance(entry, dict) and "file_id" in entry:
        return entry
    return None


def set_cached_file_id(url: str, token: str, file_id: str, media_type: str) -> None:
    """Cache file_id for a media URL."""
    cache = _load_media_cache()
    cache[_cache_key(url, token)] = {"file_id": file_id, "media_type": media_type}
    _save_media_cache(cache)


def _extract_file_id_from_send_response(resp_json: dict) -> Optional[tuple[str, str]]:
    """Extract file_id and media type from Telegram API response."""
    try:
        res = resp_json.get("result") or {}
        # Prefer explicit video/photo fields
        if "video" in res and isinstance(res["video"], dict):
            return res["video"].get("file_id"), "video"
        if "animation" in res and isinstance(res["animation"], dict):
            return res["animation"].get("file_id"), "video"
        if "photo" in res and isinstance(res["photo"], list) and res["photo"]:
            # Telegram returns a list of sizes; use the last (largest)
            return res["photo"][-1].get("file_id"), "photo"
        if "document" in res and isinstance(res["document"], dict):
            # Sometimes videos come as document
            mime = res["document"].get("mime_type", "")
            media_type = "photo" if mime.startswith("image/") else "video"
            return res["document"].get("file_id"), media_type
    except Exception:
        return None
    return None
# --- END: Simple local cache ---


async def send_video_placeholder(
    chat_id: Union[int, str],
    token: str,
    video_path: str,
    caption: Optional[str] = None,
) -> Optional[dict]:
    """Sends a local video file as a placeholder and returns the full response."""
    BASE_URL = f"https://api.telegram.org/bot{token}"
    telegram_url = f"{BASE_URL}/sendVideo"

    try:
        with open(video_path, "rb") as video_file:
            files = {"video": (os.path.basename(video_path), video_file, "video/mp4")}
            data: dict[str, Any] = {"chat_id": chat_id}
            if caption:
                data["caption"] = caption

            response = await _request_with_fixed_retry(
                client.post, telegram_url, data=data, files=files
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to send video placeholder to {chat_id}: {response.text}")
                return None
    except FileNotFoundError:
        logger.error(f"Video placeholder file not found at: {video_path}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred in send_video_placeholder: {e}")
        return None


async def send_animation_placeholder(
    chat_id: Union[int, str],
    token: str,
    animation_path: str,
    caption: Optional[str] = None,
) -> Optional[dict]:
    """Sends a local GIF file as a placeholder and returns the full response."""
    BASE_URL = f"https://api.telegram.org/bot{token}"
    telegram_url = f"{BASE_URL}/sendAnimation"

    try:
        with open(animation_path, "rb") as anim_file:
            files = {"animation": (os.path.basename(animation_path), anim_file, "image/gif")}
            data: dict[str, Any] = {"chat_id": chat_id}
            if caption:
                data["caption"] = caption

            response = await _request_with_fixed_retry(
                client.post, telegram_url, data=data, files=files
            )
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to send animation placeholder to {chat_id}: {response.text}")
                return None
    except FileNotFoundError:
        logger.error(f"Animation placeholder file not found at: {animation_path}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred in send_animation_placeholder: {e}")
        return None


async def edit_message_media(
    chat_id: Union[int, str],
    message_id: int,
    token: str,
    image_url: str,
    caption: Optional[str] = None,
):
    """Edits an existing message to replace its media with a new photo from a URL."""
    BASE_URL = f"https://api.telegram.org/bot{token}"
    telegram_url = f"{BASE_URL}/editMessageMedia"

    media = {"type": "photo", "media": image_url}
    if caption is not None:
        media["caption"] = caption

    params = {
        "chat_id": chat_id,
        "message_id": message_id,
        "media": json.dumps(media),
    }

    response = await _request_with_fixed_retry(client.post, telegram_url, json=params)
    if response.status_code != 200:
        logger.error(
            f"Failed to edit message media for message {message_id} in chat {chat_id}: {response.text}"
        )
    return response


async def download_and_send_image(url: str, chat_id: Union[int, str], is_unsafe: bool, token: str, caption: Optional[str] = None):
    """
    Download and send an image (or video) to a Telegram chat.
    
    This function implements a multi-step approach:
    1. Try sending by cached file_id (fastest)
    2. Try sending by URL directly to Telegram
    3. Fallback: download and upload as a file
    """
    is_unsafe = False # TODO: remove this after testing

    if is_unsafe and False:  # commented out until bot can send paid content
        data = {
            "chat_id": chat_id,
            "star_count": 1,
            "media": json.dumps([{"type": "photo", "media": url}]),
            "caption": "Привет!",
            "protect_content": True,
        }
        telegram_url = f"https://api.telegram.org/bot{token}/sendPaidMedia"
        response = await _request_with_fixed_retry(client.post, telegram_url, data=data)
        response.raise_for_status()

        print(f"Paid image sent successfully: {response.json()}")
        return

    # Try cache first: send by cached file_id (fast path)
    try:
        file_extension = url.split(".")[-1].lower()
        is_video = file_extension in ["mp4", "mov", "avi"]
        cached = get_cached_file_id(url, token)
        if cached and cached.get("file_id"):
            media_type_cached = cached.get("media_type") or ("video" if is_video else "photo")
            if media_type_cached == "video":
                data = {"chat_id": chat_id, "video": cached["file_id"], "caption": caption}
                telegram_url = f"https://api.telegram.org/bot{token}/sendVideo"
            else:
                data = {"chat_id": chat_id, "photo": cached["file_id"], "has_spoiler": is_unsafe, "caption": caption}
                telegram_url = f"https://api.telegram.org/bot{token}/sendPhoto"
            resp = await _request_with_fixed_retry(client.post, telegram_url, data=data)
            if resp.status_code == 200:
                logger.info("Media sent successfully from cache (file_id)")
                return
            else:
                logger.warning(f"Sending by cached file_id failed, will retry by URL. Response: {resp.text}")
    except Exception as e_cache_send:
        logger.warning(f"Cached send failed, will fallback: {e_cache_send}")

    # --- START: Normalize URL ---
    try:
        parsed = urllib.parse.urlsplit(url)
        normalized_path = re.sub(r"/+", "/", parsed.path)
        # Keep leading slash for path, rebuild URL
        url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, normalized_path, parsed.query, parsed.fragment))
    except Exception:
        pass
    # --- END: Normalize URL ---

    # --- START: Truncate caption if it's too long ---
    truncated_caption = caption
    if caption and len(caption) > 1024:
        truncated_caption = caption[:1021] + "..."
        logger.warning(f"Original caption was too long ({len(caption)} chars). Truncated for chat_id {chat_id}.")
        sentry_sdk.capture_message(
            f"Original caption was too long ({len(caption)} chars). Truncated for chat_id {chat_id}.",
            level="info",
        )
    # --- END: Truncate caption if it's too long ---
    # --- START: Prefer sending by URL directly to Telegram to avoid download+reupload ---
    try:
        file_extension = url.split(".")[-1].lower()
        is_video = file_extension in ["mp4", "mov", "avi"]
        if url.startswith("http://") or url.startswith("https://"):
            if is_video:
                data = {"chat_id": chat_id, "video": url, "caption": truncated_caption}
                telegram_url = f"https://api.telegram.org/bot{token}/sendVideo"
            else:
                data = {"chat_id": chat_id, "photo": url, "has_spoiler": is_unsafe, "caption": truncated_caption}
                telegram_url = f"https://api.telegram.org/bot{token}/sendPhoto"

            response = await _request_with_fixed_retry(client.post, telegram_url, data=data)
            if response.status_code == 200:
                resp_json = response.json()
                logger.info(f"Media sent successfully by URL: {resp_json}")
                try:
                    parsed_file = _extract_file_id_from_send_response(resp_json)
                    if parsed_file and parsed_file[0]:
                        set_cached_file_id(url, token, parsed_file[0], parsed_file[1])
                except Exception:
                    pass
                return
            else:
                logger.warning(f"Sending by URL failed, will fallback to upload. Response: {response.text}")
    except Exception as e_url:
        logger.warning(f"Sending media by URL failed with error, will fallback to upload: {e_url}")
    # --- END: Prefer sending by URL ---

    # Fallback: download and upload as a file
    response = await _request_with_fixed_retry(client.get, url)
    if response.status_code != 200:
        logger.error(f"Failed to download media from {url}: {response.text}")
        return

    file_extension = url.split(".")[-1].lower()
    is_video = file_extension in ["mp4", "mov", "avi"]

    file_content = io.BytesIO(response.content)
    file_content.name = f"downloaded_media.{file_extension}"

    if is_video:
        files = {"video": (file_content.name, file_content, "video/mp4")}
        data = {"chat_id": chat_id, "caption": truncated_caption}
        telegram_url = f"https://api.telegram.org/bot{token}/sendVideo"
    else:
        files = {"photo": (file_content.name, file_content, "image/jpeg")}
        data = {"chat_id": chat_id, "has_spoiler": is_unsafe, "caption": truncated_caption}
        telegram_url = f"https://api.telegram.org/bot{token}/sendPhoto"

    try:
        response = await _request_with_fixed_retry(client.post, telegram_url, data=data, files=files)
        if response.status_code != 200:
            logger.error(f"Failed to send media to Telegram: {response.text}")
            return
        resp_json = response.json()
        logger.info(f"Media sent successfully (uploaded): {resp_json}")
        try:
            parsed_file = _extract_file_id_from_send_response(resp_json)
            if parsed_file and parsed_file[0]:
                set_cached_file_id(url, token, parsed_file[0], parsed_file[1])
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Failed to send media to Telegram: {str(e)}")
        return

