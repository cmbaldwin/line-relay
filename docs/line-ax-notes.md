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

## Open questions (need LINE frontmost to answer)
- Does the window tree appear once LINE is active? Does Qt expose chat list rows, composer, attach/send buttons?
- If not: fall back to keyboard (Cmd+F, Enter) + screenshot checks (plan b/c in the spec).
