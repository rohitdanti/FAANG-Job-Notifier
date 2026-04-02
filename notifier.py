"""
Telegram notification sender.
Sends formatted Apple job alerts via the Telegram Bot API.
"""

import httpx

import config

TELEGRAM_API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


async def send_job_alert(job: dict) -> bool:
    """Send a single job notification to Telegram. Returns True on success."""
    title = job.get("title", "Unknown Position")
    team = job.get("team", "Apple")
    location = job.get("location", "Location not specified")
    posted = job.get("posted", "")
    role_number = job.get("role_number", "")
    weekly_hours = job.get("weekly_hours", "")
    url = job.get("url", "")

    lines = [
        "🍎 *New Apple Job Opening*",
        "",
        f"📌 *{_escape_md(title)}*",
        f"🏢 {_escape_md(team)}",
        f"📍 {_escape_md(location)}",
    ]
    if posted:
        lines.append(f"🗓 {_escape_md(posted)}")
    if role_number:
        lines.append(f"🆔 `{_escape_md(role_number)}`")
    if weekly_hours:
        lines.append(f"⏱ {_escape_md(weekly_hours)}")
    if url:
        lines.extend(["", f"[Apply on Apple Jobs]({url})"])

    return await _send_message("\n".join(lines), parse_mode="MarkdownV2")


async def send_summary(new_count: int, total_scraped: int) -> bool:
    """Send a summary message after a scraping run with new jobs."""
    message = (
        "📊 *Apple Jobs Scan Complete*\n\n"
        f"• New jobs found: *{new_count}*\n"
        f"• Total jobs scanned: *{total_scraped}*"
    )
    return await _send_message(message, parse_mode="MarkdownV2")


async def send_error(error_msg: str) -> bool:
    """Send an error notification."""
    message = f"⚠️ *Apple Jobs Scraper Error*\n\n`{_escape_md(error_msg)}`"
    return await _send_message(message, parse_mode="MarkdownV2")


async def send_plain(text: str) -> bool:
    """Send a plain text message (no Markdown)."""
    return await _send_message(text, parse_mode="")


async def verify_bot() -> bool:
    """Verify the Telegram bot token is valid. Returns True if OK."""
    if not config.TELEGRAM_BOT_TOKEN:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{TELEGRAM_API}/getMe")
            return resp.status_code == 200 and resp.json().get("ok", False)
    except httpx.HTTPError:
        return False


async def _send_message(text: str, parse_mode: str = "MarkdownV2") -> bool:
    """Low-level Telegram sendMessage call."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[notifier] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set - skipping notification.")
        return False

    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
        "disable_web_page_preview": False,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)
            if resp.status_code == 200 and resp.json().get("ok"):
                return True
            print(f"[notifier] Telegram API error: {resp.status_code} - {resp.text}")
            if parse_mode and resp.status_code == 400:
                payload["parse_mode"] = ""
                payload["text"] = text.replace("*", "").replace("`", "").replace("\\", "")
                resp2 = await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)
                return resp2.status_code == 200
            return False
    except httpx.HTTPError as exc:
        print(f"[notifier] HTTP error sending Telegram message: {exc}")
        return False


def _escape_md(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special = r"_*[]()~`>#+-=|{}.!"
    escaped = ""
    for ch in text:
        if ch in special:
            escaped += f"\\{ch}"
        else:
            escaped += ch
    return escaped
