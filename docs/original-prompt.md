# Original build prompt (verbatim)

Build "line-relay": a local MCP server on THIS Mac that sends LINE messages from my personal
LINE account by driving the LINE desktop app. It runs only on this computer: stdio transport,
started by the Claude desktop app. No network listener, no remote access.

## Context
- LINE has no API for personal accounts, so this is UI automation of the LINE macOS app,
  which is logged in here with my personal account.
- Volume is low (a few messages a day). Reliability and safety over speed.

## Requirements
1. MCP server over stdio (Python with the official `mcp` SDK, or Swift). It must not open any
   network port.
2. Tools:
   - `find_chat(query)`: search chats by name and return matches with a stable identifier and the
     last message preview. Japanese names must work (e.g. テストグループ).
   - `read_chat(chat, limit=20)`: return the latest messages (sender, time, text). Best effort.
   - `prepare_message(chat, text, attachments[])`: open the chat, attach local files (absolute paths,
     e.g. ~/Downloads/invoice.pdf), and type the text, but DO NOT SEND. Return a screenshot of the
     composed message plus a one-time `confirm_id`.
   - `send_prepared(confirm_id)`: send only that exact prepared message, and only if the chat and the
     draft still match (check by screenshot or accessibility tree). confirm_id expires in 5 minutes.
   - `cancel_prepared(confirm_id)`: clear the draft.
   - `status()`: whether LINE is running and logged in, which chat is focused, and the last error.
3. Automation approach, in this order of preference:
   a) the macOS Accessibility API (AXUIElement via pyobjc or Swift) for the search field, chat list,
      composer, attach button and send button;
   b) fall back to keyboard shortcuts (Cmd+F search, Enter to send) plus AppleScript to focus LINE;
   c) last resort, screenshot + click by coordinates, with a screenshot check before each step.
   Before writing the tools, investigate what LINE's accessibility tree actually exposes and write
   it up in docs/line-ax-notes.md.
4. Safety:
   - Never send without a matching prepare/confirm pair. No "send directly" tool.
   - Rate limit: max 20 sends per hour, max 1 per 10 s.
   - Log every prepare/send/cancel (time, chat, text, attachment names, result) to
     ~/Library/Logs/line-relay/log.jsonl.
   - If anything looks off (wrong chat, LINE update changed the UI, login prompt, LINE not running),
     stop and return an error with a screenshot. Never guess.
   - Leave the LINE window as it was found when done (restore the previously focused chat if possible).
5. Install:
   - Add it to the Claude desktop config (claude_desktop_config.json) as a local stdio server.
     Back up the config first.
   - Document the Accessibility and Screen Recording permissions it needs (for the Python/Swift
     binary that Claude launches).
6. README: setup, permissions, the Claude desktop config entry, and a test checklist.

## Test plan
- Send a text, an image and a PDF to my own Keep chat (or a test chat) end to end.
- Japanese chat search.
- An expired or mismatched confirm_id does not send.
- With LINE closed, status() and prepare_message() return clear errors.

Ask me before installing anything system-wide, granting permissions or editing the Claude config.
Work in ~/Dev/line-relay and commit as you go.
