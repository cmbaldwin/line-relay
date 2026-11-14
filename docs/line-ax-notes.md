# LINE macOS accessibility notes (in progress)

Env: LINE.app (Qt-based; menu items carry `qt_itemFired:`), Python 3.13 venv, pyobjc. Probe: `axdump.py`.

## Findings so far (LINE running, NOT frontmost, window not on the active Space)
- Process has AX trust (`AXIsProcessTrusted()` True for the launching terminal).
- App element `AXWindows` = empty, even though `AXMainWindow`/`AXFocusedWindow` return an element.
  `AXChildren` = only two `AXMenuBar`s (app menu + menu extra). No window/chat UI exposed.
- Setting `AXEnhancedUserInterface` / `AXManualAccessibility` on the app: unsupported (-25208 / -25205).
- Quartz sees the main window: title "LINE", 961x843 at (8,38), `onscreen` = None (other Space/occluded).
- Menus: LINE > Settings, Log out, Quit; View > Friends/Chats/My profile; Windows lists open chat windows
  (e.g. "<chat name>"); menu-extra has "Keep Memo".
- Cmd+F / menu-driven navigation possible via View > Chats (menu AXPress works without focus).

## Findings with LINE frontmost (activate via `osascript -e 'tell application "LINE" to activate'`)
- **LINE must be frontmost** (or at least on the current Space) or `AXWindows` is empty. Unavailable AX when backgrounded.
- `AXWindows` = 2 (main "LINE" window + one auxiliary). Main window is `AXStandardWindow`.
- Window children: top-bar `AXRadioButton`s (Friends / Chats, N), `AXButton`s (Settings, Keep Memo, Capture screen),
  and one `AXSplitGroup`:
  - `AXTextField` title "Search for chats and messages" (chat search).
  - `AXList` of `AXRow` (chat list). Each row has one `AXButton`, title = `"<chat name>, <last message preview>, <date>"`,
    actions AXPress/AXShowMenu. Japanese names come through intact. No separate identifier: use name + position;
    the stable id we hand out is a hash of the chat name.
  - Header buttons: `AXButton` titled `"<chat name>, N people"` (group) identifies the focused chat; also "Search chat", "More".
  - Inner `AXSplitGroup`: message `AXList` (rows contain `AXStaticText`, value `"<Sender>, <text>"`; time not on the row text),
    composer `AXTextArea` title "Enter a message" (focused by default), buttons "Send file", "Keep Memo", "Stickers".
    No titled Send button; Enter sends.
- Menus (`qt_itemFired:`) work, e.g. Windows > chat window names.
- Plan: AX for search/rows/composer/messages; AXPress on row to open chat; AXValue set on composer for text;
  "Send file" opens an NSOpenPanel -> Cmd+Shift+G + path + Enter (keyboard fallback, b); Enter via CGEvent to send.
  Screenshot (Screen Recording) for prepare/verify.

## Still to verify while building
- Is the composer `AXValue` settable (else paste via clipboard)?
- Attach flow through the open panel; message timestamps.
