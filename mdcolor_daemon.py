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
MODEL_FILE = os.path.expanduser("~/.claude/mdcolor_model")

RESET = "\033[0m"
GRAY = 250
DEFAULT_MODEL = "en_core_web_sm"    # small model is fast and, given full-sentence
# context, as accurate as md/trf in practice. Any installed spaCy English model works;
# change with: echo en_core_web_trf > ~/.claude/mdcolor_model  (then restart the daemon)
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


def active_model():
    """spaCy model to load: $MDCOLOR_MODEL, else MODEL_FILE, else the default.

    Read once at daemon startup (the model is loaded once and kept warm), so
    changing it takes effect on the next daemon restart, not per request.
    """
    name = os.environ.get("MDCOLOR_MODEL")
    if name:
        return name
    try:
        with open(MODEL_FILE) as f:
            n = f.read().strip()
        if n:
            return n
    except OSError:
        pass
    return DEFAULT_MODEL


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


def _clean_line(body):
    """Strip inline-markup delimiters from a prose line, keeping the inner words.

    Returns (clean, omap, inspan): `clean` is the delimiter-free text handed to the
    tagger (so spaCy sees a natural sentence, not `**word**` or `` `word` ``);
    omap[i] is the original offset of clean char i; inspan[i] is True when that char
    came from inside an inline span (kept for context but never colored). Removing
    the markup -- rather than blanking it to spaces -- matters: the small model is
    whitespace-sensitive, so injected multi-space gaps flip noun/verb guesses.

    Fixes context-blind mis-tagging: the old code split each line on inline spans
    and tagged the fragments, so spaCy lost sentence context and guessed
    noun/verb-ambiguous words wrong ("scores", "colors", "reads" -> NOUN).
    """
    clean, omap, inspan, pos = [], [], [], 0
    for m in SKIP_RE.finditer(body):
        for k in range(pos, m.start()):
            clean.append(body[k]); omap.append(k); inspan.append(False)
        span = m.group()
        a = m.start() + (len(span) - len(span.lstrip("`*_")))
        b = m.end() - (len(span) - len(span.rstrip("`*_")))
        for k in range(a, b):
            clean.append(body[k]); omap.append(k); inspan.append(True)
        pos = m.end()
    for k in range(pos, len(body)):
        clean.append(body[k]); omap.append(k); inspan.append(False)
    return "".join(clean), omap, inspan


def _color_line(body, colors):
    clean, omap, inspan = _clean_line(body)
    wraps = []
    for tok in _NLP(clean):
        if not tok.is_alpha or inspan[tok.idx]:
            continue
        s, e = omap[tok.idx], omap[tok.idx + len(tok.text) - 1] + 1
        wraps.append((s, e, colors.get(tok.pos_, GRAY)))
    if not wraps:
        return body
    out, prev = [], 0
    for s, e, code in wraps:
        out.append(body[prev:s])
        out.append(f"\033[38;5;{code}m{body[s:e]}{RESET}")
        prev = e
    out.append(body[prev:])
    return "".join(out)


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
            out.append(prefix + _color_line(line[len(prefix):], colors))
    return "\n".join(out)


def main():
    global _NLP
    import spacy
    _NLP = spacy.load(active_model(), disable=["ner", "lemmatizer"])

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
