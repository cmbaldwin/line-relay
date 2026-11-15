"""line-relay: local stdio MCP server. Sends LINE messages only via prepare -> confirm. No network listener."""
import json, os, secrets, threading, time
from collections import deque
from mcp.server.fastmcp import FastMCP, Image
from line_ax import Line, LineError, status as ax_status

mcp = FastMCP("line-relay")
LOG = os.path.expanduser("~/Library/Logs/line-relay/log.jsonl")
TTL, MAX_PER_HOUR, MIN_GAP = 300, 20, 10
prepared = {}          # confirm_id -> dict(chat, text, attachments, expires)
sends = deque()        # timestamps of sends
last_error = None
lock = threading.Lock()  # one UI operation at a time


def log(event, **kw):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "event": event, **kw}, ensure_ascii=False) + "\n")


def fail(e, line=None):
    """Return an error with a screenshot when possible. Never guess."""
    global last_error
    last_error = str(e)
    out = [f"ERROR: {e}"]
    try:
        if line:
            out.append(Image(data=line.screenshot(), format="png"))
    except Exception:
        pass
    return out


@mcp.tool()
def status() -> dict:
    """Whether LINE is running/usable, which chat is focused, and the last error."""
    s = ax_status() | {"last_error": last_error, "pending_prepared": len(prepared)}
    if s["running"]:
        try:
            with lock, Line() as l:
                s["focused_chat"] = l.focused_chat()
                s["logged_in"] = True
        except LineError as e:
            s["logged_in"], s["error"] = False, str(e)
    return s


@mcp.tool()
def find_chat(query: str) -> list | str:
    """Search chats by name (Japanese OK). Returns chat name, stable id and last message preview."""
    with lock:
        try:
            with Line() as l:
                res = l.search(query)
                out = [{"id": Line.chat_id(r["chat"]), "chat": r["chat"], "preview": r["preview"], "date": r["date"]} for r in res]
                l.clear_search()
                cur = l.focused_chat()  # the open chat's row is opaque to AX in search results
                if cur and query.lower() in cur.lower() and all(o["chat"] != cur for o in out):
                    out.insert(0, {"id": Line.chat_id(cur), "chat": cur, "preview": "(currently open)", "date": ""})
                return out
        except LineError as e:
            return fail(e)


@mcp.tool()
def read_chat(chat: str, limit: int = 20) -> list | str:
    """Latest messages of a chat (exact chat name from find_chat). Best effort: sender and text; no timestamps."""
    with lock:
        try:
            with Line() as l:
                l.open_chat(chat)
                return l.messages(limit)
        except LineError as e:
            return fail(e)


@mcp.tool()
def prepare_message(chat: str, text: str, attachments: list[str] = []) -> list:
    """Open the chat, attach files (absolute paths), type text. Does NOT send. Returns screenshot + confirm_id (valid 5 min)."""
    paths = [os.path.expanduser(p) for p in attachments]
    with lock:
        l = None
        try:
            for p in paths:
                if not os.path.isabs(p) or not os.path.isfile(p):
                    raise LineError(f"attachment must be an existing absolute path: {p}")
            with Line() as l:
                l.open_chat(chat)
                for p in paths:
                    l.attach(p)
                if text:
                    l.set_draft(text)
                cid = secrets.token_urlsafe(8)
                prepared[cid] = dict(chat=chat, text=text, attachments=paths, expires=time.time() + TTL)
                shot = l.screenshot()
            log("prepare", chat=chat, text=text, attachments=[os.path.basename(p) for p in paths], confirm_id=cid, result="ok")
            return [f"confirm_id={cid} (expires in 5 min). Check the screenshot, then call send_prepared.", Image(data=shot, format="png")]
        except LineError as e:
            log("prepare", chat=chat, text=text, attachments=[os.path.basename(p) for p in paths], result=f"error: {e}")
            return fail(e, l)


@mcp.tool()
def send_prepared(confirm_id: str) -> list:
    """Send exactly the prepared message, only if the chat and draft still match and the confirm_id is fresh."""
    with lock:
        p = prepared.get(confirm_id)
        if not p:
            log("send", confirm_id=confirm_id, result="rejected: unknown confirm_id")
            return ["ERROR: unknown or already used confirm_id. Nothing sent."]
        if time.time() > p["expires"]:
            prepared.pop(confirm_id)
            log("send", chat=p["chat"], confirm_id=confirm_id, result="rejected: expired")
            return ["ERROR: confirm_id expired. Nothing sent; call prepare_message again."]
        now = time.time()
        while sends and now - sends[0] > 3600:
            sends.popleft()
        if len(sends) >= MAX_PER_HOUR or (sends and now - sends[-1] < MIN_GAP):
            log("send", chat=p["chat"], confirm_id=confirm_id, result="rejected: rate limit")
            return ["ERROR: rate limit (20/hour, 1 per 10 s). Nothing sent; retry later (confirm_id still valid until expiry)."]
        l = None
        try:
            with Line() as l:
                if l.focused_chat() != p["chat"]:
                    raise LineError(f"focused chat is {l.focused_chat()!r}, prepared for {p['chat']!r}. Nothing sent.")
                if l.draft() != p["text"]:
                    raise LineError("composer text no longer matches the prepared draft. Nothing sent.")
                l.press_enter()
                time.sleep(1.0)
                shot = l.screenshot()
            prepared.pop(confirm_id)
            sends.append(time.time())
            log("send", chat=p["chat"], text=p["text"], attachments=[os.path.basename(a) for a in p["attachments"]], confirm_id=confirm_id, result="sent")
            return ["Sent.", Image(data=shot, format="png")]
        except LineError as e:
            log("send", chat=p["chat"], confirm_id=confirm_id, result=f"error: {e}")
            return fail(e, l)


@mcp.tool()
def cancel_prepared(confirm_id: str) -> str:
    """Discard a prepared message and clear the composer draft."""
    with lock:
        p = prepared.pop(confirm_id, None)
        if not p:
            return "unknown confirm_id (nothing to cancel)"
        try:
            with Line() as l:
                if l.focused_chat() == p["chat"]:
                    l.clear_draft()
            result = "cancelled"
        except LineError as e:
            result = f"cancelled (draft not cleared: {e})"
        log("cancel", chat=p["chat"], text=p["text"], confirm_id=confirm_id, result=result)
        return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
