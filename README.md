# line-relay

Local stdio MCP server that drives the LINE macOS app (personal account) via the Accessibility API.
No network listener. Sending needs `prepare_message` -> `send_prepared(confirm_id)`; there is no direct send.

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
