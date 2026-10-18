import os
import sys
from datetime import datetime, time, timedelta

from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer as FastMCP
from telethon import TelegramClient

# Make sure `src` package is importable when the file is run directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

from src.scrapper.Telegram.get_by_day import get_by_day  # noqa: E402
from src.scrapper.Telegram.get_unread import scrape_unread_messages  # noqa: E402
from src.scrapper.Telegram.list_groups import list_groups  # noqa: E402

ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.env"))
load_dotenv(ENV_PATH)
load_dotenv()


mcp = FastMCP("tbridge")

SESSION_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../scrapper/Telegram/job_scraper_session")
)


def _make_client() -> TelegramClient:
    api_id_raw = os.getenv("Telegram_API_ID", "")
    return TelegramClient(
        SESSION_PATH,
        int(api_id_raw) if api_id_raw.isdigit() else 0,
        os.getenv("Telegram_API_Hash") or "",
    )


# Module-level client, initialized once when the MCP server starts.
# All tool calls share this single connected instance — valid because mcp.run()
# keeps a single async event loop alive for the lifetime of the server process.
_client: TelegramClient = _make_client()


async def _get_client() -> TelegramClient:
    """Return the shared client, reconnecting if the connection dropped."""
    if not _client.is_connected():
        await _client.connect()
    return _client


async def _assert_authorized(client: TelegramClient) -> None:
    """Raise a clear error if the session is missing or expired."""
    if not await client.is_user_authorized():
        raise RuntimeError(
            "Telegram session is not authorized. "
            "Run `uv run python src/scrapper/Telegram/auth.py` to re-authenticate."
        )


@mcp.tool()
async def scrape_telegram_group(
    target: str,
    days_back: int = 0,
    start_time: str | None = None,
    end_time: str | None = None,
    mark_read: bool = False,
) -> dict:
    """
    Scrape text messages from a Telegram group you are a member of.

    Two ways to specify the time range (start_time/end_time take priority over days_back):

    1. Custom range — pass start_time and/or end_time as ISO 8601 strings:
         start_time="2026-10-14T00:00:00"  end_time="2026-10-16T23:59:59"
         start_time="2026-10-16T18:00:00"  (end_time omits → now)
       Times without a timezone offset are treated as local time.

    2. Whole-day shortcut — pass days_back (ignored when start_time is given):
         days_back=0  → today,  days_back=1 → yesterday, etc.

    Args:
        target:     The exact group name, @username, or numeric ID.
        days_back:  Whole-day fallback. 0 = today, 1 = yesterday, etc.
        start_time: ISO 8601 range start, e.g. "2026-10-16T09:00:00".
        end_time:   ISO 8601 range end,   e.g. "2026-10-16T18:00:00".
                    Defaults to now when start_time is given but end_time is omitted.
        mark_read:  If True, marks fetched messages as read on Telegram after scraping.
                    Defaults to False — always confirm with the user before setting this to True.

    Returns:
        A dict with:
            - 'messages': list of {msg_id, peer_id, date (ISO 8601), message}
            - 'count':    {total, text_msg, other_msg}
    """
    LOCAL_TZ = datetime.now().astimezone().tzinfo

    if start_time is not None:
        # Parse ISO 8601; attach local timezone if none provided
        start = datetime.fromisoformat(start_time)
        if start.tzinfo is None:
            start = start.replace(tzinfo=LOCAL_TZ)

        if end_time is not None:
            end = datetime.fromisoformat(end_time)
            if end.tzinfo is None:
                end = end.replace(tzinfo=LOCAL_TZ)
        else:
            end = datetime.now().astimezone(LOCAL_TZ)
    else:
        # Whole-day fallback using days_back
        base_date = datetime.now().date() - timedelta(days=days_back)
        start = datetime.combine(base_date, time.min).replace(tzinfo=LOCAL_TZ)
        end   = datetime.combine(base_date, time.max).replace(tzinfo=LOCAL_TZ)

    client = await _get_client()
    await _assert_authorized(client)
    return await get_by_day(target, start, end, client, mark_read=mark_read)


@mcp.tool()
async def get_unread_messages(target: str, mark_read: bool = False) -> dict:
    """
    Scrape only the unread messages from a Telegram group you are a member of.

    Args:
        target:    The exact group name as it appears in your Telegram sidebar.
        mark_read: If True, marks fetched messages as read on Telegram after scraping.
                   Defaults to False — always confirm with the user before setting this to True.

    Returns:
        A dict with:
            - 'messages': list of {msg_id, peer_id, date (ISO 8601), message}
            - 'count':    {total, text_msg, other_msg}
    """
    client = await _get_client()
    await _assert_authorized(client)
    return await scrape_unread_messages(target, client, mark_read=mark_read)


@mcp.tool()
async def list_telegram_groups(include_archived: bool = False) -> list[dict]:
    """
    List all groups and channels the user is a member of.

    Args:
        include_archived: If True, includes archived chats in the result.
                          Defaults to False.

    Returns:
        A list of dicts with: id, name, type ('group' | 'channel'), unread_count, archived.
    """
    client = await _get_client()
    await _assert_authorized(client)
    return await list_groups(client, include_archived=include_archived)


if __name__ == "__main__":
    mcp.run()  # stdio transport — one persistent event loop, shared client across all tool calls
