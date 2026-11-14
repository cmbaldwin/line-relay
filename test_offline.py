"""Offline safety checks (no LINE UI touched): bad/expired confirm_id must not send."""
import time, server
r = server.send_prepared("nope"); assert "unknown" in r[0]
server.prepared["x"] = dict(chat="c", text="t", attachments=[], expires=time.time() - 1)
r = server.send_prepared("x"); assert "expired" in r[0] and "x" not in server.prepared
print("ok")
