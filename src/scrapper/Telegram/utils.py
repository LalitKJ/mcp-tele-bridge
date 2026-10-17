from telethon import TelegramClient
from telethon.tl.types import (
    User, Chat, Channel, ChatForbidden, ChannelForbidden
)
from typing import Union

# Single concrete entity type that iter_messages and iter_messages accept
Entity = Union[User, Chat, Channel, ChatForbidden, ChannelForbidden]

def _serialize_message(message, peer_id: int) -> dict:
    """Convert a Telethon Message object to a JSON-serializable dict."""
    # sender is only populated when the message was fetched with sender info;
    # fall back to None rather than raising if it's missing
    sender = message.sender
    if sender is not None:
        sender_name = (
            getattr(sender, "first_name", None)
            or getattr(sender, "title", None)   # channels/groups have title, not first_name
            or getattr(sender, "username", None)
        )
        sender_username = getattr(sender, "username", None)
    else:
        sender_name = None
        sender_username = None

    return {
        "msg_id":          message.id,
        "peer_id":         peer_id,
        "date":            message.date.isoformat(),
        "message":         message.message or "",
        "sender_id":       message.sender_id,
        "sender_name":     sender_name,
        "sender_username": sender_username,
    }


async def _find_dialog(target: str | int, client: TelegramClient):
    """Return the dialog object matching target name or ID, or None."""
    async for dialog in client.iter_dialogs():
        match = dialog.id == target if isinstance(target, int) else dialog.name == target
        if match:
            return dialog
    return None


async def _resolve_entity(target: str | int, client: TelegramClient):
    """Fast entity resolution — use for scraping by date (no unread_count needed)."""
    if isinstance(target, int) or (isinstance(target, str) and target.startswith("@")):
        try:
            entity = await client.get_entity(target)
            # get_entity() can return a list if passed a sequence — ensure single entity
            if isinstance(entity, list):
                return entity[0] if entity else None
            return entity
        except Exception:
            return None
    # Fall back to dialog scan for plain display names
    async for dialog in client.iter_dialogs():
        if dialog.name == target:
            return dialog.entity
    return None
