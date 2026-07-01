#!/usr/bin/env python3
"""Claude Code MessageDisplay hook: always-on per-word POS coloring in the chat.

Every assistant message is recolored by part of speech, inline in the terminal:
nouns and verbs get distinct hues, adjectives/adverbs get dimmed variants of each,
and everything else is a quiet gray. The heavy lifting (spaCy) runs in a warm
daemon (mdcolor_daemon.py) so each message is a fast local socket round-trip
instead of paying spaCy's multi-second cold start every time.

How it works
------------
MessageDisplay fires once per streaming delta. This hook accumulates the deltas
per message_id, suppresses the streaming chunks, and on the final chunk replaces
the whole message with the colored version.

Kill switch
-----------
Create ~/.claude/mdcolor_off to disable coloring instantly (messages then stream
and display normally). Delete it to re-enable. No restart needed.

Renderer caveat
---------------
The chat renderer shows markdown AND embedded ANSI together, but the moment any
ANSI color is present it drops to inline-only markdown: **bold**, `inline code`
and ```code fences``` still render, but block headers (##) and tables show as raw
symbols. Coloring therefore skips code fences, table rows and inline spans, but it
cannot preserve header/table structure in a colored message. This is a renderer
limitation, not a bug.

Fail-clean
----------
If the daemon cannot be started or coloring fails for any reason, the original
text is shown unchanged, so the chat is never broken.
"""
import sys, json, os, re, socket, subprocess, time

UID = os.getuid()
HERE = os.path.dirname(os.path.abspath(__file__))
CLAUDE_DIR = os.path.expanduser("~/.claude")

ACC_DIR = os.environ.get("MDCOLOR_ACC_DIR", "/tmp/mdcolor_%d_acc" % UID)
SOCK = os.environ.get("MDCOLOR_SOCK", "/tmp/mdcolor_%d.sock" % UID)
OFF_FLAG = os.path.join(CLAUDE_DIR, "mdcolor_off")
DAEMON = os.path.join(HERE, "mdcolor_daemon.py")
DAEMON_LOG = os.path.join(CLAUDE_DIR, "mdcolor_daemon.log")


def emit(dc=None):
    if dc is not None:
        sys.stdout.write(json.dumps(
            {"hookSpecificOutput": {"hookEventName": "MessageDisplay", "displayContent": dc}}))
    sys.exit(0)


def _send(text):
    c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    c.connect(SOCK)
    c.sendall(text.encode("utf-8"))
    c.shutdown(socket.SHUT_WR)
    buf = []
    while True:
        b = c.recv(65536)
        if not b:
            break
        buf.append(b)
    c.close()
    return b"".join(buf).decode("utf-8", "replace")


def colorize(text):
    """Colorize via the daemon; cold-start it once if needed. None on failure."""
    try:
        return _send(text)
    except OSError:
        pass
    try:
        os.makedirs(CLAUDE_DIR, exist_ok=True)
        with open(DAEMON_LOG, "a") as log:
            subprocess.Popen([sys.executable, DAEMON], start_new_session=True,
                             stdout=log, stderr=subprocess.STDOUT)
    except Exception:
        return None
    for _ in range(40):                  # wait out spaCy cold start (~4s), then give up
        time.sleep(0.2)
        try:
            return _send(text)
        except OSError:
            continue
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        emit()

    if os.path.exists(OFF_FLAG):
        emit()                           # kill switch -> display original, stream normally

    delta = data.get("delta", "") or ""
    final = bool(data.get("final", False))
    mid = re.sub(r"[^A-Za-z0-9_-]", "_", str(data.get("message_id", "x")))

    os.makedirs(ACC_DIR, exist_ok=True)
    acc_path = os.path.join(ACC_DIR, mid)
    with open(acc_path, "a") as f:
        f.write(delta)
    if not final:
        emit("")                         # suppress streaming; colored version lands on final
    with open(acc_path) as f:
        text = f.read()
    try:
        os.remove(acc_path)
    except OSError:
        pass

    colored = colorize(text)
    emit(colored if colored is not None else text)   # fail-clean to original


if __name__ == "__main__":
    main()
