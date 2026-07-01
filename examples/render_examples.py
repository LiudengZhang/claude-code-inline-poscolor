#!/usr/bin/env python3
"""Render the README example SVGs from the *real* spaCy tagging + palette codes.

Two outputs, both driven by the same PALETTES dict the daemon uses, so they can
never drift from the actual tool:
  - before-after.svg : one sentence plain-gray, then POS-colored
  - palettes.svg     : the same sentence under all five palettes

Regenerate:  python3 examples/render_examples.py
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
from mdcolor_daemon import PALETTES, GRAY, DEFAULT_PALETTE   # single source of truth

import spacy

SENTENCE = "The pipeline scores every patient quickly and writes clean results."
BG = "#0d1117"          # GitHub-dark terminal panel; palette hues are tuned for dark
FONT = "ui-monospace, 'SF Mono', 'Cascadia Code', Menlo, Consolas, monospace"
FS = 15                 # font size
CHARW = 9.02            # monospace advance at FS=15
LH = 30                 # line height
PAD = 18


def xterm_hex(code):
    """xterm-256 color code -> #rrggbb."""
    if code < 16:
        base = [0, 95, 135, 175, 215, 255]
        return "#%02x%02x%02x" % (base[1] if code & 1 else 0,
                                  base[1] if code & 2 else 0,
                                  base[1] if code & 4 else 0)
    if code >= 232:
        v = 8 + (code - 232) * 10
        return "#%02x%02x%02x" % (v, v, v)
    n = code - 16
    lv = [0, 95, 135, 175, 215, 255]
    return "#%02x%02x%02x" % (lv[n // 36], lv[(n % 36) // 6], lv[n % 6])


NLP = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer"])
DOC = NLP(SENTENCE)


def pos_codes(palette_name):
    noun, adj, verb, adv = PALETTES[palette_name]
    return {"NOUN": noun, "PROPN": noun, "ADJ": adj, "VERB": verb, "ADV": adv}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def tspans(palette_name=None):
    """Colored <tspan>s for the sentence; palette_name=None => all gray."""
    codes = pos_codes(palette_name) if palette_name else {}
    out = []
    for tok in DOC:
        code = codes.get(tok.pos_, GRAY) if tok.is_alpha else GRAY
        out.append('<tspan fill="%s">%s</tspan>' % (xterm_hex(code), esc(tok.text_with_ws)))
    return "".join(out)


def text_el(x, y, inner, fill=None):
    f = ' fill="%s"' % fill if fill else ""
    return ('<text x="%g" y="%g" xml:space="preserve" font-family="%s" '
            'font-size="%d"%s>%s</text>') % (x, y, FONT, FS, f, inner)


def svg(width, height, body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%g" height="%g" '
            'viewBox="0 0 %g %g" role="img">'
            '<rect width="%g" height="%g" rx="8" fill="%s"/>%s</svg>\n'
            % (width, height, width, height, width, height, BG, body))


def write(name, content):
    path = os.path.join(HERE, name)
    with open(path, "w") as f:
        f.write(content)
    print("wrote", os.path.relpath(path))


# --- before-after.svg -------------------------------------------------------
sent_w = len(SENTENCE) * CHARW
label_w = 9 * CHARW                              # "colored " column
W = PAD * 2 + label_w + sent_w
rows = [("plain", tspans(None)), ("colored", tspans(DEFAULT_PALETTE))]
body = []
for i, (label, inner) in enumerate(rows):
    y = PAD + FS + i * LH
    body.append(text_el(PAD, y, esc(label), fill=xterm_hex(GRAY)))
    body.append(text_el(PAD + label_w, y, inner))
write("before-after.svg", svg(W, PAD * 2 + LH * len(rows), "".join(body)))

# --- palettes.svg -----------------------------------------------------------
names = list(PALETTES)
label_w = 14 * CHARW                             # widest name "teal-magenta" + gap
W = PAD * 2 + label_w + sent_w
body = []
for i, name in enumerate(names):
    y = PAD + FS + i * LH
    tag = name + (" *" if name == DEFAULT_PALETTE else "")
    body.append(text_el(PAD, y, esc(tag), fill=xterm_hex(GRAY)))
    body.append(text_el(PAD + label_w, y, tspans(name)))
write("palettes.svg", svg(W, PAD * 2 + LH * len(names), "".join(body)))
