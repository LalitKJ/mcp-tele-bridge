# tbridge 🚀

> **Autonomous Telegram Automation Agent & Model Context Protocol (FastMCP) Server**
> Repository: `mcp-tele-bridge` | Application: `tbridge`

[![Python Version](https://img.shields.io/badge/python-3.12%20%7C%203.14-blue.svg)](pyproject.toml)
[![Protocol](https://img.shields.io/badge/protocol-MCP%20(Model%20Context%20Protocol)-green.svg)](https://modelcontextprotocol.io/)
[![Client](https://img.shields.io/badge/telethon-1.45%2B-orange.svg)](https://github.com/LonamiWebs/Telethon)
[![Package Manager](https://img.shields.io/badge/uv-managed-purple.svg)](https://github.com/astral-sh/uv)

**tbridge** (`mcp-tele-bridge`) bridges Telegram's real-time messaging ecosystem directly with modern AI agents (Claude Desktop, Cursor, VS Code, and custom LLM workflows) using the open **[Model Context Protocol (MCP)](https://modelcontextprotocol.io/)**.

Operating as a native Telegram user-client via Telethon (MTProto), tbridge turns private channel and group memberships into an actionable tool suite that agents can inspect, query, scrape, and filter autonomously.

---

## Table of Contents

- [The Big Idea](#the-big-idea)
- [Key Features](#key-features)
- [Architecture & Implementation](#architecture--implementation)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
  - [1. Clone & Install Dependencies](#1-clone--install-dependencies)
  - [2. Telegram API Credentials](#2-telegram-api-credentials)
  - [3. Configure Environment](#3-configure-environment)
  - [4. One-Time Authentication](#4-one-time-authentication)
- [MCP Integration](#mcp-integration)
  - [Claude Desktop Configuration](#claude-desktop-configuration)
  - [Cursor / VS Code MCP Configuration](#cursor--vs-code-mcp-configuration)
  - [Running the MCP Server Directly](#running-the-mcp-server-directly)
- [Tool Reference](#tool-reference)
  - [`list_telegram_groups`](#list_telegram_groups)
  - [`get_unread_messages`](#get_unread_messages)
  - [`scrape_telegram_group`](#scrape_telegram_group)
- [Storage & Deduplication](#storage--deduplication)
- [Example Workflows](#example-workflows)
- [Security & Best Practices](#security--best-practices)
- [Contributing & Roadmap](#contributing--roadmap)

---

## The Big Idea

Telegram hosts some of the most dynamic, high-value real-time feeds available—developer announcements, tech job referrals, product feedback, market signals, and specialized community groups. However:

1. **Volume Overload**: High-frequency groups bury critical opportunities and signals under thousands of conversational messages.
2. **Bot vs. User Limitations**: Standard Telegram bots require admin privileges or explicit invitations to every channel, cannot read private user memberships, and cannot access restricted feeds.
3. **Agent Isolation**: Modern AI models and coding assistants lack native protocols to interact with Telegram chats in real time.

### How tbridge Solves This

tbridge runs as an **authenticated user client (MTProto)** under your own Telegram account while exposing standardized tools via **FastMCP** over standard I/O (`stdio`).

```
┌──────────────────────────────────────────────────────────────────┐
│                         AI Agent Host                            │
│           (Claude Desktop / Cursor / Custom LLM Agent)          │
└─────────────────────────────────┬────────────────────────────────┘
                                  │ MCP (JSON-RPC over stdio)
                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│                     tbridge FastMCP Server                       │
│                   src/agent/tools/telegram_tool.py               │
└───────┬─────────────────────────┬─────────────────────────┬──────┘
        │                         │                         │
        ▼                         ▼                         ▼
┌──────────────┐          ┌──────────────┐          ┌──────────────┐
│ Dialog List  │          │ Unread Fetch │          │ Date-Bounded │
│ list_groups  │          │  get_unread  │          │  get_by_day  │
└───────┬──────┘          └───────┬──────┘          └───────┬──────┘
        └─────────────────────────┼─────────────────────────┘
                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│                   Telethon User Client (MTProto)                 │
│              Local Session: job_scraper_session.session          │
└─────────────────────────────────┬────────────────────────────────┘
                                  │ Encrypted MTProto
                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│                       Telegram Cloud API                         │
│            (Channels, Supergroups, Discussion Feeds)            │
└──────────────────────────────────────────────────────────────────┘
```

Your AI assistant can now:
- Discover all available channels and groups without hardcoding chat IDs.
- Fetch only unread messages or query specific temporal windows (e.g., "today", "yesterday", or exact ISO 8601 timestamps).
- Selectively mark messages as read only up to the exact batch processed.
- Filter, classify, and persist extracted data (e.g., into deduplicated CSVs) for downstream agent actions.

---

## Key Features

- **Standard FastMCP Server**: Built on the official `mcp[cli]` specification using `stdio` transport. Compatible with any MCP client (Claude Desktop, Cursor, Claude Code, LibreChat, etc.).
- **User-Client Telethon (MTProto)**: Interacts as a verified Telegram account rather than a bot. Accesses every group and channel your personal account belongs to.
- **Persistent Connection Management**: Single async event loop with intelligent reconnection and session authorization guards (`_assert_authorized`).
- **Precision Unread Tracking**: Telethon dialog tracking to ingest *only* unread messages, chronologically ordered (oldest unread first), with targeted `send_read_acknowledge`.
- **Timezone-Aware Temporal Filters**: Query messages by whole-day shortcuts (`days_back=0` for today, `days_back=1` for yesterday) or custom ISO 8601 date-time spans with automatic UTC normalization.
- **Flexible Entity Resolution**: Target groups by exact display title (e.g., `"Tech Referrals & Jobs"`), public handle (e.g., `"@techjobs"`), or numeric channel/group ID (`-100...`).
- **Clean JSON Serialization**: Normalizes raw Telethon message entities into predictable schemas containing message ID, peer ID, ISO timestamp, text, and sender details (`sender_id`, `sender_name`, `sender_username`).
- **Idempotent Storage**: Built-in CSV writer engine with pandas-powered deduplication on `msg_id` to prevent duplicate ingestion across multiple runs.

---

## Architecture & Implementation

tbridge is structured into modular layers designed for reliability, clarity, and separation of concerns:

### 1. Protocol Layer (`src/agent/tools/telegram_tool.py`)
- Initializes a FastMCP instance (`tbridge`).
- Maintains a single, long-lived `TelegramClient` connection across MCP tool calls within the server's lifecycle.
- Handles parameter parsing, local timezone resolution, and error translation.

### 2. Scraping & MTProto Engine (`src/scrapper/Telegram/`)
- **`auth.py`**: CLI utility for one-time interactive phone/code login. Stores credentials in `.session` file.
- **`list_groups.py`**: Iterates dialogs via `client.iter_dialogs()`, filtering out private 1-on-1 chats and bots while capturing unread counts, chat types (`group` vs `channel`), and archive statuses.
- **`get_unread.py`**: Reads `dialog.unread_count`, fetches exactly the unread slice via `client.iter_messages(limit=unread)`, and reverses it for chronological processing.
- **`get_by_day.py`**: Uses Telegram's native `offset_date` with `reverse=True` to jump directly to the target timestamp and iterate forward, terminating as soon as `end_utc` is crossed.
- **`utils.py`**: Fast entity resolution supporting usernames, numeric IDs, and fallback dialog scans. Also performs safe sender extraction and message serialization.

### 3. Storage Layer (`src/storage/csv_writer.py`)
- `save_messages()`: Appends new rows to designated CSV files. Reads existing `msg_id`s to skip duplicates automatically.

---

## Project Structure

```text
mcp-tele-bridge/
├── .env.example                  # Template for Telegram API credentials
├── .gitignore                    # Ignores sessions, virtualenvs, local data
├── .python-version               # Python version pin (>=3.12 / 3.14)
├── pyproject.toml                # Project metadata & dependencies
├── README.md                     # Documentation
├── uv.lock                       # Deterministic dependency lockfile
└── src/
    ├── __init__.py
    ├── agent/
    │   ├── __init__.py
    │   └── tools/
    │       ├── __init__.py
    │       └── telegram_tool.py  # FastMCP Server & exposed tool declarations
    ├── scrapper/
    │   ├── __init__.py
    │   └── Telegram/
    │       ├── __init__.py
    │       ├── auth.py           # Interactive Telegram session authenticator
    │       ├── get_by_day.py     # Date-range message scraper
    │       ├── get_unread.py     # Unread-only message scraper
    │       ├── list_groups.py    # Group & channel enumerator
    │       └── utils.py          # Entity resolution & serialization
    └── storage/
        ├── __init__.py
        └── csv_writer.py         # Deduplicating CSV persistence engine
```

---

## Prerequisites

- **Python**: Version `3.12` or higher (tested up to Python `3.14`).
- **Package Manager**: [`uv`](https://github.com/astral-sh/uv) (recommended for speed and lockfile support) or standard `pip`.
- **Telegram Account**: A personal Telegram account and API credentials.

---

## Getting Started

### 1. Clone & Install Dependencies

Using `uv` (recommended):

```bash
git clone https://github.com/LalitKJ/mcp-tele-bridge.git
cd mcp-tele-bridge

# Create virtual environment and install dependencies from uv.lock
uv sync
```

Alternatively, using standard `pip`:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Telegram API Credentials

To access Telegram via MTProto, obtain your `api_id` and `api_hash`:

1. Log in to [https://my.telegram.org](https://my.telegram.org).
2. Navigate to **API development tools**.
3. Create a new application (e.g., App title: `tbridge`, Short name: `tbridge`).
4. Copy the **App api_id** (numeric) and **App api_hash** (string).

### 3. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
Telegram_API_ID="12345678"
Telegram_API_Hash="your_telegram_api_hash_here"
```

### 4. One-Time Authentication

Authenticate your Telegram session locally:

```bash
uv run python src/scrapper/Telegram/auth.py
```

- When prompted, enter your phone number with country code (e.g., `+1234567890`).
- Enter the confirmation code sent to your Telegram app (and your two-step verification cloud password if enabled).
- Once completed, your credentials are saved to `src/scrapper/Telegram/job_scraper_session.session`.

> ⚠️ **Security Note**: Never commit or share your `.session` file! It contains full authorization to your Telegram account. It is ignored by `.gitignore` by default.

---

## MCP Integration

Once authenticated, connect tbridge to your favorite AI host.

### Claude Desktop Configuration

Open your Claude Desktop configuration file:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Add `tbridge` under the `mcpServers` object:

```json
{
  "mcpServers": {
    "tbridge": {
      "command": "uv",
      "args": [
        "--directory",
        "E:/Projects/mcp-tele-bridge",
        "run",
        "python",
        "src/agent/tools/telegram_tool.py"
      ]
    }
  }
}
```

*(Ensure you replace `E:/Projects/mcp-tele-bridge` with the absolute path to your repository clone).*

Restart Claude Desktop. You will see the hammer/tools icon indicating that `tbridge` tools are ready to use.

### Cursor / VS Code MCP Configuration

In `.cursor/mcp.json` or your VS Code MCP extension settings:

```json
{
  "mcpServers": {
    "tbridge": {
      "command": "uv",
      "args": [
        "--directory",
        "${workspaceFolder}",
        "run",
        "python",
        "src/agent/tools/telegram_tool.py"
      ]
    }
  }
}
```

### Running the MCP Server Directly

For testing or debugging stdio communication:

```bash
uv run python src/agent/tools/telegram_tool.py
```

---

## Tool Reference

tbridge exposes three core tools through the Model Context Protocol:

### `list_telegram_groups`

Discovers and lists all channels and groups your account is currently joined to.

- **Parameters**:
  - `include_archived` *(bool, optional)*: Set to `true` to include archived chats. Defaults to `false`.
- **Returns**: A list of chat descriptors:
  ```json
  [
    {
      "id": -1001234567890,
      "name": "Backend Engineers & DevOps",
      "type": "channel",
      "unread_count": 42,
      "archived": false
    }
  ]
  ```

---

### `get_unread_messages`

Fetches only the unread messages from a targeted group or channel.

- **Parameters**:
  - `target` *(string, required)*: The group/channel display name, `@username`, or numeric ID.
  - `mark_read` *(bool, optional)*: If `true`, marks fetched messages as read on Telegram up to the latest retrieved message ID. Defaults to `false`.
- **Returns**:
  ```json
  {
    "count": {
      "total": 5,
      "text_msg": 5,
      "other_msg": 0
    },
    "messages": [
      {
        "msg_id": 9812,
        "peer_id": 1234567890,
        "date": "2026-10-18T08:30:00+00:00",
        "message": "Senior Python/AI Engineer needed at TechCorp...",
        "sender_id": 987654321,
        "sender_name": "Alice HR",
        "sender_username": "alice_recruiter"
      }
    ]
  }
  ```

---

### `scrape_telegram_group`

Scrapes messages within a defined temporal window or whole-day duration.

- **Parameters**:
  - `target` *(string, required)*: Target group name, `@username`, or numeric ID.
  - `start_time` *(string, optional)*: Inclusive start ISO 8601 timestamp (e.g., `"2026-10-18T09:00:00"`). Local timezone assumed if omitted.
  - `end_time` *(string, optional)*: Exclusive end ISO 8601 timestamp. Defaults to `now` when `start_time` is provided.
  - `days_back` *(int, optional)*: Whole-day shortcut when `start_time` is omitted. `0` = today (00:00:00 to 23:59:59), `1` = yesterday, etc.
  - `mark_read` *(bool, optional)*: If `true`, marks messages up to the latest fetched message as read. Defaults to `false`.
- **Returns**: Same structure as `get_unread_messages`.

---

## Storage & Deduplication

In addition to returning structured tool payloads to LLMs, tbridge provides a robust persistence helper in `src/storage/csv_writer.py`.

```python
from src.storage.csv_writer import save_messages

messages = [...]  # Serialized message dicts from tool response
rows_written = save_messages(messages, "jobs.csv")
print(f"Appended {rows_written} new rows.")
```

- **Idempotency**: It checks existing `msg_id` values in the destination CSV and skips duplicates.
- **Safe Headers**: Automatically writes the CSV header only when initializing a new file or appending to an empty file.

---

## Example Workflows

### 1. Autonomous Job & Tech Referral Filter
Ask your AI agent:
> *"Check the 'Tech Referral Network' group for unread messages. Filter for Senior Backend or AI Engineer roles offering over 15 LPA or $100k, summarize the requirements and direct application contacts, and mark them as read."*

The agent calls:
1. `list_telegram_groups()` to locate the chat.
2. `get_unread_messages(target="Tech Referral Network", mark_read=True)`.
3. Synthesizes and presents the filtered roles.

### 2. Daily Community Digest
Ask your AI agent:
> *"Fetch all messages posted yesterday in @python_developers. Highlight the top 3 technical discussions, open-source libraries mentioned, and user questions."*

The agent calls:
1. `scrape_telegram_group(target="@python_developers", days_back=1)`.
2. Processes and clusters topics into an executive digest.

---

## Security & Best Practices

- **Session Confidentiality**: The `.session` file is equivalent to an active login token. Never upload it to version control, cloud storage, or untrusted machines.
- **Telegram Rate Limits**: Avoid excessive high-speed loops over dozens of large channels to prevent Telegram FloodWait errors. Telethon handles standard rate limits gracefully, but prudent batching is recommended.
- **Read State Safety**: Always default `mark_read=False` unless you intentionally want the agent to clear unread counters in your personal Telegram client.

---

## Contributing & Roadmap

Contributions, suggestions, and issue reports are welcome!

### Potential Future Enhancements
- [ ] Support for media extraction (PDF resume parsing, image OCR).
- [ ] Interactive Telegram message sending tool via MCP (`send_telegram_message`).
- [ ] Webhook / long-polling event triggers for push-based agent notification.
- [ ] SQLite / vector database storage integration for semantic search over historical chats.

---

## License

This project is licensed under the MIT License — see the repository for details.
