#!/usr/bin/env python3
"""Persistent spaCy POS-coloring daemon for the MessageDisplay hook.

Loads en_core_web_sm once and keeps it warm, so the hook can colorize each
finished message via a fast Unix-socket round-trip instead of paying spaCy's
~4s cold start every time. Exits after an idle period so it does not linger.
Auto-(re)started by the hook when absent.

Protocol: client connects, sends UTF-8 text, half-closes (SHUT_WR); the daemon
returns the ANSI-colored text and closes the connection.

Palette: the active palette name is read from ~/.claude/mdcolor_palette on every
request (falling back to the default), so switching palettes is instant and needs
no restart. Each palette is two families -- a noun hue + its dimmed adjective, and
a verb hue + its dimmed adverb -- plus a constant gray for everything else.
"""
import os, re, socket

SOCK = os.environ.get("MDCOLOR_SOCK", "/tmp/mdcolor_%d.sock" % os.getuid())
IDLE = int(os.environ.get("MDCOLOR_IDLE", "3600"))  # seconds idle before exit
PALETTE_FILE = os.path.expanduser("~/.claude/mdcolor_palette")

RESET = "\033[0m"
GRAY = 250
DEFAULT_PALETTE = "cyan-orange"
# name -> (noun/propn, adjective, verb, adverb)   [256-color codes]
PALETTES = {
    "cyan-orange":  (45, 31, 208, 130),
    "pink-green":   (205, 168, 40, 28),
    "gold-purple":  (220, 136, 129, 91),
    "blue-yellow":  (33, 24, 226, 178),
    "teal-magenta": (44, 30, 201, 163),
}

LEAD_RE = re.compile(r"^\s*(?:#{1,6}\s+|[-*+]\s+|\d+\.\s+|>\s+)?")
SKIP_RE = re.compile(r"(`[^`]*`|\*\*[^*]+\*\*|\*[^*]+\*|__[^_]+__|_[^_]+_)")
FENCE_RE = re.compile(r"^\s*```")

_NLP = None


def active_colors():
    """POS -> code map for the palette named in PALETTE_FILE (default otherwise)."""
    name = DEFAULT_PALETTE
    try:
        with open(PALETTE_FILE) as f:
            n = f.read().strip()
        if n in PALETTES:
            name = n
    except OSError:
        pass
    noun, adj, verb, adv = PALETTES[name]
    return {"NOUN": noun, "PROPN": noun, "ADJ": adj, "VERB": verb, "ADV": adv}


def color_segment(seg, colors):
    out = []
    for tok in _NLP(seg):
        if tok.is_alpha:
            code = colors.get(tok.pos_, GRAY)
            out.append(f"\033[38;5;{code}m{tok.text}{RESET}{tok.whitespace_}")
        else:
            out.append(tok.text_with_ws)
    return "".join(out)


def color_body(body, colors):
    parts = SKIP_RE.split(body)
    for i, part in enumerate(parts):
        if i % 2 == 1 or not part:          # matched inline span -> leave literal
            continue
        parts[i] = color_segment(part, colors)
    return "".join(parts)


def colorize(text):
    colors = active_colors()
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
            out.append(prefix + color_body(line[len(prefix):], colors))
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
