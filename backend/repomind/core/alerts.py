from __future__ import annotations

import json
import logging
import smtplib
import time
from email.message import EmailMessage
from typing import Any

import httpx
from repomind.core.config import get_settings

LOGGER = logging.getLogger("repomind.alerts")


def send_alert(event: str, fields: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    payload = {"event": event, "fields": fields, "ts": round(time.time(), 3)}
    results = []
    if settings.alert_webhook_url:
        results.append(_send_webhook(settings.alert_webhook_url, payload))
    if settings.alert_slack_webhook_url:
        results.append(_send_webhook(settings.alert_slack_webhook_url, _slack_payload(payload)))
    if settings.alert_email_to and settings.alert_email_from and settings.alert_smtp_host:
        results.append(_send_email(payload))
    if not results:
        LOGGER.info("alert_not_configured %s", json.dumps(payload, sort_keys=True))
    return {"event": event, "deliveries": results}


def _send_webhook(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        response = httpx.post(url, json=payload, timeout=5)
        return {
            "transport": "webhook",
            "status_code": response.status_code,
            "ok": response.is_success,
        }
    except Exception as exc:
        LOGGER.exception("alert_webhook_failed")
        return {"transport": "webhook", "ok": False, "error": str(exc)}


def _send_email(payload: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    message = EmailMessage()
    message["Subject"] = f"RepoMindAI alert: {payload['event']}"
    message["From"] = settings.alert_email_from or ""
    message["To"] = settings.alert_email_to or ""
    message.set_content(json.dumps(payload, indent=2, sort_keys=True))
    try:
        with smtplib.SMTP(settings.alert_smtp_host, settings.alert_smtp_port, timeout=8) as smtp:
            smtp.starttls()
            if settings.alert_smtp_username and settings.alert_smtp_password:
                smtp.login(settings.alert_smtp_username, settings.alert_smtp_password)
            smtp.send_message(message)
        return {"transport": "email", "ok": True}
    except Exception as exc:
        LOGGER.exception("alert_email_failed")
        return {"transport": "email", "ok": False, "error": str(exc)}


def _slack_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "text": f"RepoMindAI alert: {payload['event']}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*RepoMindAI alert:* `{payload['event']}`\n```{json.dumps(payload['fields'], sort_keys=True)}```",
                },
            }
        ],
    }
