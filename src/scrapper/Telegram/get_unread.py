from telethon import TelegramClient
from typing import Any

from .utils import _serialize_message, _find_dialog


async def scrape_unread_messages(
    target: str | int,
    client: TelegramClient,
    mark_read: bool = False,
) -> dict:
    """
    Scrape only the unread messages from a Telegram group.

    Telethon tracks unread_count per dialog — this fetches exactly those
    messages without needing a date range.

    Args:
        target: Group name (str) or numeric ID (int).
        client: An already-connected TelegramClient instance.

    Returns:
        { "messages": [{msg_id, peer_id, date, message}, ...], "count": {...} }
    """
    dialog = await _find_dialog(target, client)
    if not dialog:
        raise ValueError(f"Could not find '{target}' in your chat list.")

    unread = dialog.unread_count
    if unread == 0:
        return {"messages": [], "count": {"total": 0, "text_msg": 0, "other_msg": 0}}

    message_store: list[dict] = []
    count = {"total": 0, "text_msg": 0, "other_msg": 0}
    last_msg_id: int | None = None

    # limit=unread fetches exactly the last N (unread) messages, newest first
    async for message in client.iter_messages(dialog.id, limit=unread):
        # Track the first message in the loop — it's the newest (highest ID)
        if last_msg_id is None:
            last_msg_id = message.id
        count["total"] += 1
        if message.raw_text:
            message_store.append(_serialize_message(message, dialog.id))
            count["text_msg"] += 1
        else:
            count["other_msg"] += 1

    # Reverse so messages are in chronological order (oldest unread first)
    message_store.reverse()

    if mark_read and last_msg_id is not None:
        # max_id marks only up to the last fetched message, not the whole chat
        await client.send_read_acknowledge(dialog.id, max_id=last_msg_id)

    return {"messages": message_store, "count": count}
