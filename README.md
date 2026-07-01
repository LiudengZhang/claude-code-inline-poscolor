# claude-code-inline-poscolor

Always-on, **inline part-of-speech coloring** for [Claude Code](https://claude.com/claude-code).
Every assistant message is recolored **in the terminal chat itself** — nouns and
verbs get distinct hues, adjectives and adverbs get dimmed variants of each, and
everything else fades to a quiet gray. Built for faster, ADHD-friendly reading.

```
The pipeline scores every patient quickly and writes clean results.
    ^cyan     ^orange       ^cyan  ^orange(dim)        ^cyan
```

| Part of speech | Color        | 256-code |
|----------------|--------------|----------|
| noun / proper  | bright cyan  | 45       |
| adjective      | dim cyan     | 31       |
| verb           | bright orange| 208      |
| adverb         | dim orange   | 130      |
| everything else| light gray   | 250      |

Nouns and verbs are deliberately opposite hues; adjectives sit in the noun
family (dimmed) and adverbs in the verb family (dimmed), so the grammar is
legible at a glance.

## How it works

Claude Code's **`MessageDisplay` hook** fires once per streaming delta and can
replace the displayed text. This project uses it in two pieces:

- **`messagedisplay_hook.py`** — accumulates the streamed deltas per message,
  suppresses the raw stream, and on the final chunk replaces the whole message
  with the colored version.
- **`mdcolor_daemon.py`** — a small daemon that loads spaCy's `en_core_web_sm`
  **once** and keeps it warm on a Unix socket. Cold start is ~4s (paid once);
  every message after that is a ~7ms round-trip. It idles out after an hour and
  the hook restarts it on demand.

Coloring runs the POS tagger and wraps each word in an ANSI 256-color escape.

## Install

Requires Python 3 and spaCy.

```bash
git clone https://github.com/liudengzhang/claude-code-inline-poscolor.git
cd claude-code-inline-poscolor
pip install -r requirements.txt      # if you don't already have spaCy
./install.sh                         # fetches the model + registers the hook
```

`install.sh` merges the hook into `~/.claude/settings.json` (it does not clobber
your other settings), downloads `en_core_web_sm` if missing, and makes the
scripts executable. Start a new Claude Code session and coloring is on.

To wire it up by hand instead, copy the `hooks.MessageDisplay` block from
[`settings.snippet.json`](settings.snippet.json) into `~/.claude/settings.json`
and set the absolute path to `messagedisplay_hook.py`.

## Kill switch

Toggle coloring instantly, no restart:

```bash
touch ~/.claude/mdcolor_off     # off  (messages stream and display normally)
rm -f ~/.claude/mdcolor_off     # on
```

## Palettes

Each palette is two families: a noun hue (noun + dimmed adjective) paired with a
verb hue (verb + dimmed adverb), plus constant gray for everything else. Five ship
built in:

| Palette | Noun / Adjective | Verb / Adverb |
|---|---|---|
| `cyan-orange` *(default)* | cyan / dim cyan | orange / dim orange |
| `pink-green` | hot pink / rose | green / dim green |
| `gold-purple` | gold / olive | purple / dim purple |
| `blue-yellow` | blue / dim blue | yellow / amber |
| `teal-magenta` | teal / dim teal | magenta / dim magenta |

Preview them all as colored sample sentences, then switch — the daemon reads the
active palette per message, so it changes instantly with no restart:

```bash
bin/palettes                 # preview every palette
bin/palettes pink-green      # set the active palette
```

The choice is stored in `~/.claude/mdcolor_palette`. To add your own, edit the
`PALETTES` dict (name -> noun, adjective, verb, adverb as 256-color codes) in
`mdcolor_daemon.py` and `bin/palettes`.

## Known limitation (read this)

The chat renderer shows markdown **and** embedded ANSI together — but the moment
any ANSI color is present it drops to **inline-only** markdown. In a colored
message:

- ✅ **bold**, `inline code`, and ```code fences``` still render
- ❌ block **headers** (`##`) and **tables** show as raw `#` / `|` symbols

The coloring deliberately skips code fences, table rows, and inline spans so they
stay clean, but it cannot preserve header/table *structure* in a message that is
also colored. This is a renderer limitation, not a bug — coloring words and
rendering a table are mutually exclusive in the same message.

Also: because streaming is suppressed and replaced on the final chunk, colored
messages appear all-at-once rather than token-by-token.

If any of this bothers you, use the kill switch and reach for the on-demand
tools below instead.

## On-demand CLI tools

Two standalone colorizers in [`bin/`](bin) for when you want full color with no
renderer limits (plain terminal output, no markdown in play):

```bash
# auto-tag any text/file by POS with spaCy
bin/pos-color notes.txt --legend

# color text you tag yourself (exact on jargon the auto-tagger misreads)
echo '<n>PARP</n> <v>inhibits</v> <n>repair</n>' | bin/colorize
#      noun          verb            noun
```

`pos-color` uses the same spaCy model and scheme automatically. `colorize` takes
hand-authored tags — `<n>` noun, `<j>` adjective, `<v>` verb, `<d>` adverb,
untagged text stays gray — which is handy when domain terms need exact control.

## Requirements

- Python 3.7+
- [spaCy](https://spacy.io) with the `en_core_web_sm` model
- A terminal with 256-color ANSI support (any modern one)

## License

MIT — see [LICENSE](LICENSE).
