import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def mask_target(target: str) -> str:
    if len(target) <= 8:
        return "***"
    if target.startswith("http"):
        return target.split("?")[0].rstrip("/")[:32] + "/***"
    return f"{target[:3]}***{target[-3:]}"


async def send_notification(channel: str, target: str, text: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            if channel == "webhook":
                resp = await client.post(target, json={"text": text})
            elif channel == "telegram":
                if not settings.telegram_bot_token:
                    logger.warning("Telegram token missing; skip target=%s", mask_target(target))
                    return False
                url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
                resp = await client.post(url, json={"chat_id": target, "text": text})
            else:
                logger.warning("Unknown notification channel: %s", channel)
                return False
            resp.raise_for_status()
            return True
    except Exception as exc:
        logger.warning("Notification failed channel=%s target=%s error=%s", channel, mask_target(target), exc)
        return False
