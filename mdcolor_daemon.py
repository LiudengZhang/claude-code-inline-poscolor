#!/usr/bin/env python3
"""Persistent spaCy POS-coloring daemon for the MessageDisplay hook.

Loads en_core_web_sm once and keeps it warm, so the hook can colorize each
finished message via a fast Unix-socket round-trip instead of paying spaCy's
~4s cold start every time. Exits after an idle period so it does not linger.
Auto-(re)started by the hook when absent.

Protocol: client connects, sends UTF-8 text, half-closes (SHUT_WR); the daemon
returns the ANSI-colored text and closes the connection.

Color scheme (256-color, two families so nouns/verbs read as opposites):
  NOUN / PROPN -> 45  bright cyan     ADJ -> 31  dim cyan   (noun family)
  VERB         -> 208 bright orange   ADV -> 130 dim orange (verb family)
  everything else            -> 250 light gray
"""
import os, re, socket

SOCK = os.environ.get("MDCOLOR_SOCK", "/tmp/mdcolor_%d.sock" % os.getuid())
IDLE = int(os.environ.get("MDCOLOR_IDLE", "3600"))  # seconds idle before exit

RESET = "\033[0m"
COLORS = {"NOUN": 45, "PROPN": 45, "ADJ": 31, "VERB": 208, "ADV": 130}
GRAY = 250
LEAD_RE = re.compile(r"^\s*(?:#{1,6}\s+|[-*+]\s+|\d+\.\s+|>\s+)?")
SKIP_RE = re.compile(r"(`[^`]*`|\*\*[^*]+\*\*|\*[^*]+\*|__[^_]+__|_[^_]+_)")
FENCE_RE = re.compile(r"^\s*```")

_NLP = None


def color_segment(seg):
    out = []
    for tok in _NLP(seg):
        if tok.is_alpha:
            code = COLORS.get(tok.pos_, GRAY)
            out.append(f"\033[38;5;{code}m{tok.text}{RESET}{tok.whitespace_}")
        else:
            out.append(tok.text_with_ws)
    return "".join(out)


def color_body(body):
    parts = SKIP_RE.split(body)
    for i, part in enumerate(parts):
        if i % 2 == 1 or not part:          # matched inline span -> leave literal
            continue
        parts[i] = color_segment(part)
    return "".join(parts)


def colorize(text):
    out, in_fence = [], False
    for line in text.split("\n"):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(line)                        # fence marker + code = literal
        elif in_fence or line.strip().startswith("|") or not line.strip():
            out.append(line)                        # code / table / blank = literal
        else:
            m = LEAD_RE.match(line)
            prefix = m.group(0)                     # keep leading ##/-/> literal
            out.append(prefix + color_body(line[len(prefix):]))
    return "\n".join(out)


def main():
    global _NLP
    import spacy
    _NLP = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])

    if os.path.exists(SOCK):
        os.remove(SOCK)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(SOCK)
    srv.listen(8)
    srv.settimeout(IDLE)
    try:
        while True:
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                break                        # idle -> exit cleanly
            with conn:
                buf = []
                while True:
                    b = conn.recv(65536)
                    if not b:
                        break
                    buf.append(b)
                text = b"".join(buf).decode("utf-8", "replace")
                try:
                    reply = colorize(text)
                except Exception:
                    reply = text             # never corrupt the message
                conn.sendall(reply.encode("utf-8"))
    finally:
        try:
            os.remove(SOCK)
        except OSError:
            pass


if __name__ == "__main__":
    main()
