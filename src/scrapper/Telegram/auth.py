# src/scrapper/Telegram/auth.py
import os
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()

SESSION_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "job_scraper_session"))

async def main():
    client: TelegramClient = TelegramClient(
        SESSION_PATH,
        int(os.getenv("Telegram_API_ID", "0")),
        os.getenv("Telegram_API_Hash") or "",
    )
    # start() returns self (TelegramClient) — Pylance flags it as not awaitable,
    # but Telethon's start() is a coroutine that returns the client. Ignore the false positive.
    await client.start()  # type: ignore[misc]

    if not await client.is_user_authorized():
        await client.disconnect()
        raise RuntimeError(
            "Authentication failed — session is not authorized after login. "
            "Check your network connection and try again."
        )

    print("✅ Authenticated! Session saved to", SESSION_PATH)
    await client.disconnect()

asyncio.run(main())
