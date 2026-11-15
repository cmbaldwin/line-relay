---
name: line-relay
description: Use whenever the user wants to send, draft, read, or look up a LINE message or chat from their personal LINE account (mentions LINE, a LINE chat/group name, "send this to ...on LINE"). Drives the local line-relay MCP server (tools find_chat, read_chat, prepare_message, send_prepared, cancel_prepared, status). Repo ~/Dev/line-relay.
---

# line-relay

Sends LINE messages by driving the LINE macOS app. Sending is irreversible and goes to real people.

## Rules
1. Never call `send_prepared` without the user's explicit OK for THAT draft in THIS conversation.
   A request like "send X to Y" counts as OK for exactly that text and chat; any change to text,
   recipient or attachments needs a new OK. Never invent or "improve" text the user dictated.
2. Flow: `find_chat(query)` if the exact chat name is unknown -> `prepare_message(chat, text, attachments)`
   -> show the user the screenshot and the exact text -> wait for OK (unless rule 1 already granted it)
   -> `send_prepared(confirm_id)` -> report the result screenshot.
3. Use the exact chat name returned by `find_chat`. If several chats match, ask. Never guess a recipient.
4. Attachments are absolute local paths. confirm_id expires after 5 min; if expired, prepare again.
5. On any error (wrong chat, login prompt, LINE not running, UI changed) stop and report it with the
   screenshot. Do not retry sending. Use `cancel_prepared` to discard a draft that is no longer wanted.
6. Limits: 20 sends/hour, 1 per 10 s. No direct-send tool exists; do not work around that.

## Practical notes
- LINE must be on the user's current Space; each call briefly brings LINE forward, then restores the previous app.
- If tools are missing: the server is in Claude's MCP config (desktop + `claude mcp add -s user`);
  Accessibility + Screen Recording permissions are needed for the launching app. See ~/Dev/line-relay/README.md.
- Log: ~/Library/Logs/line-relay/log.jsonl. Design and AX notes: ~/Dev/line-relay/docs/.
- Original build spec: ~/Dev/line-relay/docs/original-prompt.md.
