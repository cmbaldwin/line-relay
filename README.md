# line-relay

Local stdio MCP server that drives the LINE macOS app (personal account) via the Accessibility API.
No network listener. Sending needs `prepare_message` -> `send_prepared(confirm_id)`; there is no direct send.

## ⚠️ LINE terms of use: read before using
LINE offers no API for personal accounts, and its terms restrict automated or unauthorized use of the
service. A LINE account can be restricted or banned for it. line-relay is meant **only** as a personal
assistive tool that stays inside those limits as closely as possible:

- **Your own account, on your own Mac.** The LINE desktop app must already be logged in. It never
  handles credentials and never talks to LINE's servers directly.
- **A human approves every message.** Each send needs a prepared draft and an explicit confirm.
  There is no unattended or scheduled sending, and no direct-send tool.
- **Low volume.** Hard limits of 20 sends per hour and 1 per 10 s. It is for the few messages a day
  you would otherwise type yourself.
- **Not for** bulk messaging, marketing, spam, scraping, unsolicited contact, bots that answer
  automatically, or any commercial or business messaging. For those, use a
  [LINE Official Account and the Messaging API](https://developers.line.biz/en/docs/messaging-api/),
  which is LINE's supported way to automate.

You are responsible for following LINE's current terms of use. Use at your own risk. This project is
not affiliated with or endorsed by LINE / LY Corporation.

## Setup
    cd ~/Dev/line-relay && uv venv --python 3.13 .venv && uv pip install --python .venv/bin/python -r requirements.txt
    .venv/bin/python test_offline.py

## Permissions (System Settings > Privacy & Security)
The process that launches the server needs both:
- **Accessibility** (read LINE's UI, press buttons, send keys)
- **Screen Recording** (screenshots of the composed message)

When launched by Claude desktop, that is the **Claude** app (child processes inherit its grants); the
interpreter is `~/Dev/line-relay/.venv/bin/python`. If a tool reports empty windows or blank screenshots,
grant the permission and restart Claude.

## Claude desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`)
    "mcpServers": { "line-relay": {
      "command": "/path/to/line-relay/.venv/bin/python",
      "args": ["/path/to/line-relay/server.py"] } }

## Behaviour notes
- LINE must be on the current Space: its AX tree is empty otherwise. Each tool call activates LINE, then restores
  the previous app and the previously open chat. See `docs/line-ax-notes.md`.
- Limits: 20 sends/hour, 1 per 10 s. confirm_id expires after 5 min. Log: `~/Library/Logs/line-relay/log.jsonl`.
- `send_prepared` refuses if the focused chat or composer text no longer matches.

## Test checklist
- [ ] `test_offline.py` passes (bad/expired confirm_id).
- [ ] `find_chat("テストグループ")` returns the chat.
- [ ] Text to Keep/test chat: prepare -> screenshot -> send_prepared.
- [ ] Image and PDF to Keep/test chat (verify attach flow, see notes).
- [ ] Wrong/expired confirm_id sends nothing; log records rejection.
- [ ] LINE quit: `status()` and `prepare_message()` return clear errors.
- [ ] After each call the previous app/chat is restored.
