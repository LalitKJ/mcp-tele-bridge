from telethon import TelegramClient
from telethon.tl.types import Chat, Channel


async def list_groups(
    client: TelegramClient,
    include_archived: bool = False,
) -> list[dict]:
    """
    List all groups and channels the user is a member of.

    Args:
        client:           An already-connected TelegramClient instance.
        include_archived: If True, includes archived chats in the result.
                          Defaults to False.

    Returns:
        A list of dicts with: id, name, type ('group' | 'channel'), unread_count, archived.
    """
    results: list[dict] = []

    async for dialog in client.iter_dialogs():
        # Skip archived unless explicitly requested
        if dialog.archived and not include_archived:
            continue

        # Only include groups and channels, not private/bot chats
        if not isinstance(dialog.entity, (Chat, Channel)):
            continue

        entity_type = "channel" if isinstance(dialog.entity, Channel) else "group"

        results.append({
            "id": dialog.id,
            "name": dialog.name,
            "type": entity_type,
            "unread_count": dialog.unread_count,
            "archived": dialog.archived,
        })

    return results
