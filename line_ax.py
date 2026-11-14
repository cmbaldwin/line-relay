"""LINE macOS UI automation: Accessibility API first, keyboard via System Events, screenshots for verification."""
import hashlib, os, subprocess, time
from ApplicationServices import (AXUIElementCreateApplication, AXUIElementCopyAttributeValue,
                                 AXUIElementSetAttributeValue, AXUIElementPerformAction)
from AppKit import NSWorkspace
from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionAll, kCGNullWindowID


class LineError(Exception):
    pass


def g(e, a):
    err, v = AXUIElementCopyAttributeValue(e, a, None)
    return v if err == 0 else None


def osa(script):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=30)
    if r.returncode:
        raise LineError(f"osascript failed: {r.stderr.strip()}")
    return r.stdout.strip()


def _app():
    for a in NSWorkspace.sharedWorkspace().runningApplications():
        if a.localizedName() == "LINE":
            return a
    raise LineError("LINE is not running")


def frontmost():
    return osa('tell application "System Events" to get name of first application process whose frontmost is true')


def _walk(e, role, depth=6):
    if g(e, "AXRole") == role:
        yield e
    if depth:
        for c in g(e, "AXChildren") or []:
            yield from _walk(c, role, depth - 1)


class Line:
    """One instance per tool call; use as a context manager so the previous app/chat is restored."""

    def __enter__(self):
        self.prev_app = frontmost()
        self.app = _app()
        self.ax = AXUIElementCreateApplication(self.app.processIdentifier())
        self.prev_chat = None
        osa('tell application "LINE" to activate')
        self.win = self._window()
        self.prev_chat = self.focused_chat()
        return self

    def __exit__(self, *exc):
        try:
            if self.prev_chat and self.focused_chat() != self.prev_chat:
                self.open_chat(self.prev_chat)  # restore previously focused chat
        except Exception:
            pass
        if self.prev_app and self.prev_app != "LINE":
            try:
                osa(f'tell application "{self.prev_app}" to activate')
            except LineError:
                pass

    # ---- structure -------------------------------------------------------
    def _window(self):
        for _ in range(10):
            for w in g(self.ax, "AXWindows") or []:
                if g(w, "AXTitle") == "LINE" and list(_walk(w, "AXTextField", 4)):
                    return w
            time.sleep(0.3)
        raise LineError("LINE main window not found (login screen, locked, or UI changed)")

    def _split(self):
        return next(_walk(self.win, "AXSplitGroup", 2))

    def search_field(self):
        return next(_walk(self._split(), "AXTextField", 2))

    def chat_list(self):
        return next(_walk(self._split(), "AXList", 2))

    def composer(self):
        for ta in _walk(self.win, "AXTextArea", 6):
            if g(ta, "AXTitle") == "Enter a message":
                return ta
        raise LineError("composer not found (no chat open, or UI changed)")

    def focused_chat(self):
        """Header button title is '<name>, N people' for groups; for 1:1 chats it is just the name."""
        for b in _walk(self._split(), "AXButton", 2):
            t = g(b, "AXTitle") or ""
            if t and t not in ("Sort chats by", "Collapse chats", "Create chat", "Mute chat", "Open in separate window",
                               "Search chat", "Start a call", "Notes", "More"):
                return t.rsplit(", ", 1)[0] if t.endswith(" people") else t
        return None

    # ---- chats -----------------------------------------------------------
    @staticmethod
    def chat_id(name):
        return "c_" + hashlib.sha1(name.encode()).hexdigest()[:10]

    def _rows(self):
        out = []
        for r in g(self.chat_list(), "AXChildren") or []:
            for b in g(r, "AXChildren") or []:
                t = g(b, "AXTitle")
                if t:
                    parts = t.rsplit(", ", 2)  # "<name>, <preview>, <date>" (name/preview may contain commas)
                    out.append((t, b, parts))
        return out

    def search(self, query):
        f = self.search_field()
        AXUIElementSetAttributeValue(f, "AXFocused", True)
        AXUIElementSetAttributeValue(f, "AXValue", query)
        time.sleep(1.2)
        res = [{"chat": p[0] if len(p) == 3 else t, "preview": p[1] if len(p) == 3 else "", "date": p[-1], "_el": b}
               for t, b, p in self._rows()]
        return res

    def clear_search(self):
        AXUIElementSetAttributeValue(self.search_field(), "AXValue", "")

    def open_chat(self, name):
        hits = [h for h in self.search(name) if h["chat"] == name or h["chat"].startswith(name + ",")]
        if len(hits) != 1:
            self.clear_search()
            raise LineError(f"expected exactly one chat named {name!r}, found {len(hits)}")
        AXUIElementPerformAction(hits[0]["_el"], "AXPress")
        time.sleep(0.8)
        self.clear_search()
        if self.focused_chat() != name:
            raise LineError(f"opened chat is {self.focused_chat()!r}, expected {name!r}")

    # ---- messages --------------------------------------------------------
    def messages(self, limit):
        lists = [l for l in _walk(self._split(), "AXList", 4) if l is not self.chat_list()]
        msgs = []
        for r in g(lists[0], "AXChildren") or [] if lists else []:
            for t in _walk(r, "AXStaticText", 4):
                v = g(t, "AXValue")
                if v:
                    sender, _, text = v.partition(", ")
                    msgs.append({"sender": sender, "text": text})
        return msgs[-limit:]

    # ---- composing -------------------------------------------------------
    def draft(self):
        return g(self.composer(), "AXValue") or ""

    def set_draft(self, text):
        c = self.composer()
        AXUIElementSetAttributeValue(c, "AXFocused", True)
        AXUIElementSetAttributeValue(c, "AXValue", text)
        time.sleep(0.3)
        if self.draft() != text:  # Qt may ignore AXValue writes: paste instead, then restore the clipboard
            self._paste(text)
            if self.draft() != text:
                raise LineError("could not place text in composer")

    def _paste(self, text):
        old = subprocess.run(["pbpaste"], capture_output=True).stdout
        subprocess.run(["pbcopy"], input=text.encode())
        osa('tell application "System Events" to keystroke "a" using command down')
        osa('tell application "System Events" to keystroke "v" using command down')
        time.sleep(0.4)
        subprocess.run(["pbcopy"], input=old)

    def attach(self, path):
        if not os.path.isfile(path):
            raise LineError(f"attachment not found: {path}")
        btn = next(b for b in _walk(self.win, "AXButton", 6) if g(b, "AXTitle") == "Send file")
        AXUIElementPerformAction(btn, "AXPress")
        time.sleep(1.0)
        old = subprocess.run(["pbpaste"], capture_output=True).stdout
        subprocess.run(["pbcopy"], input=path.encode())
        osa('tell application "System Events"\nkeystroke "g" using {command down, shift down}\ndelay 0.6\n'
            'keystroke "v" using command down\ndelay 0.4\nkey code 36\ndelay 0.8\nkey code 36\nend tell')
        subprocess.run(["pbcopy"], input=old)
        time.sleep(1.0)

    def clear_draft(self):
        AXUIElementSetAttributeValue(self.composer(), "AXValue", "")

    def press_enter(self):
        AXUIElementSetAttributeValue(self.composer(), "AXFocused", True)
        osa('tell application "System Events" to key code 36')

    def screenshot(self):
        wid = next((w["kCGWindowNumber"] for w in CGWindowListCopyWindowInfo(kCGWindowListOptionAll, kCGNullWindowID)
                    if w["kCGWindowOwnerPID"] == self.app.processIdentifier() and w.get("kCGWindowName") == "LINE"), None)
        path = f"/tmp/line-relay-{os.getpid()}.png"
        subprocess.run(["screencapture", "-x", "-o"] + ([f"-l{wid}"] if wid else []) + [path], check=True)
        data = open(path, "rb").read()
        os.remove(path)
        return data


def status():
    try:
        app = _app()
    except LineError as e:
        return {"running": False, "error": str(e)}
    ax = AXUIElementCreateApplication(app.processIdentifier())
    return {"running": True, "frontmost": app.isActive(), "windows_visible_to_ax": len(g(ax, "AXWindows") or [])}
