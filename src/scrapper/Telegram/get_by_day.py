from telethon import TelegramClient
from datetime import datetime, timezone

from .utils import _serialize_message, _resolve_entity


async def get_by_day(
    target: str | int,
    start_time: datetime,
    end_time: datetime,
    client: TelegramClient,
    mark_read: bool = False,
) -> dict:
    """
    Scrape text messages from a Telegram group between start_time and end_time.

    Accepts a plain display name, @username, or numeric ID as target.

    Args:
        target:     Group name (str), @username (str), or numeric ID (int).
        start_time: Inclusive lower bound (timezone-aware datetime).
        end_time:   Exclusive upper bound (timezone-aware datetime).
        client:     An already-connected TelegramClient instance.
        mark_read:  If True, marks fetched messages as read after scraping.

    Returns:
        {
            "messages": [ {msg_id, peer_id, date (ISO 8601), message}, ... ],
            "count":    { total, text_msg, other_msg }
        }
    """
    entity = await _resolve_entity(target, client)
    if not entity:
        raise ValueError(f"Could not find '{target}' in your chat list.")

    entity_id = entity.id

    # Normalize both bounds to UTC for comparison with message.date (always UTC)
    start_utc = start_time.astimezone(timezone.utc)
    end_utc   = end_time.astimezone(timezone.utc)

    message_store: list[dict] = []
    count = {"total": 0, "text_msg": 0, "other_msg": 0}
    last_msg_id: int | None = None

    # offset_date + reverse=True: Telegram jumps to start_utc and iterates forward
    async for message in client.iter_messages(entity, offset_date=start_utc, reverse=True):
        if message.date > end_utc:
            break
        last_msg_id = message.id
        count["total"] += 1
        if message.raw_text:
            message_store.append(_serialize_message(message, entity_id))
            count["text_msg"] += 1
        else:
            count["other_msg"] += 1

    if mark_read and last_msg_id is not None:
        # max_id marks only up to the last fetched message, not the whole chat
        await client.send_read_acknowledge(entity, max_id=last_msg_id)

    return {"messages": message_store, "count": count}
