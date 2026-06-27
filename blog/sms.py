"""
SMS helper for musoyevschool.

Sends text messages through the free, open-source "SMS Gateway for
Android" app (sms-gate.app / github.com/capcom6/android-sms-gateway)
running in Local Server mode on an old Android phone that lives on the
same classroom network as this Django server.

Setup on the phone (one-time):
1. Install "SMS Gateway for Android" from Play Store or F-Droid.
2. Insert a SIM with SMS enabled (no data plan needed for SMS itself,
   only Wi-Fi for the local HTTP server).
3. In the app, turn on "Local Server" and tap "Offline" to start it.
4. Note the phone's local IP, port (default 8080), and the
   username/password shown on that screen.
5. On your router, give the phone a static IP / DHCP reservation so
   the gateway URL never goes stale.
6. On the phone, disable battery optimization for the app and keep
   Wi-Fi on while the screen is off, or Android will kill the local
   server in the background.

Configuration is stored in the SmsConfig model (editable via /sms-config/).
settings.py fallbacks (SMS_GATEWAY_URL, SMS_GATEWAY_USERNAME,
SMS_GATEWAY_PASSWORD) are used only if SmsConfig has no saved values.
"""

import logging
import threading

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _get_config():
    """Return (url, username, password) from SmsConfig, falling back to settings."""
    try:
        from blog.models import SmsConfig
        cfg = SmsConfig.get()
        url      = cfg.gateway_url or getattr(settings, 'SMS_GATEWAY_URL', '')
        username = cfg.username    or getattr(settings, 'SMS_GATEWAY_USERNAME', '')
        password = cfg.password    or getattr(settings, 'SMS_GATEWAY_PASSWORD', '')
    except Exception:
        url      = getattr(settings, 'SMS_GATEWAY_URL', '')
        username = getattr(settings, 'SMS_GATEWAY_USERNAME', '')
        password = getattr(settings, 'SMS_GATEWAY_PASSWORD', '')
    return url, username, password


def normalize_phone(raw):
    """Best-effort normalize a typed-in number to +998XXXXXXXXX.

    The parent_phone field is free text today, so teachers may enter
    "90 123 45 67", "901234567", or "+998901234567". This keeps the
    gateway from silently rejecting numbers that are missing the
    country code.
    """
    if not raw:
        return None
    digits = "".join(ch for ch in raw if ch.isdigit())
    if raw.strip().startswith("+"):
        return f"+{digits}"
    if len(digits) == 9:
        return f"+998{digits}"
    if digits.startswith("998") and len(digits) == 12:
        return f"+{digits}"
    return f"+{digits}" if digits else None


def _post_to_gateway(phone_numbers, text):
    """Send SMS via the Android gateway. Reads config fresh from DB each call."""
    url, username, password = _get_config()

    if not url:
        logger.warning("SMS gateway URL sozlanmagan — xabar yuborilmadi.")
        return

    endpoint = f"{url.rstrip('/')}/message"
    payload  = {"textMessage": {"text": text}, "phoneNumbers": phone_numbers}
    try:
        response = requests.post(
            endpoint,
            json=payload,
            auth=(username, password),
            timeout=8,
        )
        response.raise_for_status()
        logger.info("SMS queued on gateway for %s", phone_numbers)
    except requests.RequestException as exc:
        # The phone being offline/charging/out of Wi-Fi range must never
        # break attendance saving or assessment saving, so we only log.
        logger.warning("SMS gateway unreachable, message to %s not sent: %s", phone_numbers, exc)


def send_sms(phone_numbers, text):
    """Queue a text message to one or more parents.

    Fire-and-forget: runs the HTTP call to the phone in a background
    thread so a slow or unreachable gateway never makes a teacher wait
    on the attendance or assessment page.
    """
    numbers = [normalize_phone(n) for n in phone_numbers]
    numbers = [n for n in numbers if n]
    if not numbers:
        return
    threading.Thread(target=_post_to_gateway, args=(numbers, text), daemon=False).start()