import logging
import smtplib
from email.message import EmailMessage

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def mask_target(target: str) -> str:
    if len(target) <= 8:
        return "***"
    if target.startswith("http"):
        return target.split("?")[0].rstrip("/")[:32] + "/***"
    return f"{target[:3]}***{target[-3:]}"


def _send_email(target: str, text: str) -> bool:
    if not settings.smtp_host or not settings.smtp_user or not settings.smtp_password:
        logger.warning("SMTP config missing; skip target=%s", mask_target(target))
        return False

    msg = EmailMessage()
    msg["Subject"] = "二手行情价格提醒"
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = target
    msg.set_content(text)

    with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)
    return True


def _send_sms(target: str, text: str) -> bool:
    logger.warning("SMS provider is not configured yet; skip target=%s text=%s", mask_target(target), text[:32])
    return False


async def send_notification(channel: str, target: str, text: str) -> bool:
    try:
        if channel == "email":
            return _send_email(target, text)
        if channel == "sms":
            return _send_sms(target, text)

        async with httpx.AsyncClient(timeout=20.0) as client:
            if channel == "webhook":
                resp = await client.post(target, json={"text": text})
            elif channel == "feishu":
                resp = await client.post(
                    target,
                    json={
                        "msg_type": "text",
                        "content": {"text": text},
                    },
                )
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
