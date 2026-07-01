# claude-code-inline-poscolor

Always-on **part-of-speech coloring** for [Claude Code](https://claude.com/claude-code).
Every assistant message is recolored right in the terminal: nouns and verbs get distinct
hues, adjectives and adverbs dimmed variants of each, everything else a quiet gray. Built
for faster, ADHD-friendly reading.

**[简体中文](README.zh-Hans.md) · [繁體中文](README.zh-Hant.md)**

| Part of speech | Color *(default palette)* | 256-code |
|---|---|---|
| noun / proper | bright cyan | 45 |
| adjective | dim cyan | 31 |
| verb | bright orange | 208 |
| adverb | dim orange | 130 |
| everything else | gray | 250 |

## Install

```bash
git clone https://github.com/LiudengZhang/claude-code-inline-poscolor.git
cd claude-code-inline-poscolor
pip install -r requirements.txt
./install.sh          # fetches the model + registers the MessageDisplay hook
```

Start a new Claude Code session and coloring is on. `install.sh` merges the hook into
`~/.claude/settings.json` without clobbering your other settings.

## How it works

A `MessageDisplay` hook (`src/messagedisplay_hook.py`) accumulates each streamed message
and, on the final chunk, replaces it with the colored version. A warm spaCy daemon
(`src/mdcolor_daemon.py`) keeps `en_core_web_sm` loaded, so each message is a ~7 ms socket
round-trip after a one-time ~4 s cold start. Fail-clean: if the daemon can't start, the
original text is shown unchanged.

## Controls

```bash
touch ~/.claude/mdcolor_off                       # disable instantly (rm to re-enable)
bin/palettes                                      # preview 5 palettes
bin/palettes pink-green                           # switch (instant, no restart)
echo en_core_web_trf > ~/.claude/mdcolor_model    # change model (then restart the daemon)
```

## On-demand CLI

```bash
bin/pos-color notes.txt --legend                          # auto-tag a file by POS
echo '<n>PARP</n> <v>inhibits</v> <n>repair</n>' | bin/colorize   # tag it yourself
```

## Known limitation

The chat renderer drops to inline-only markdown the moment any ANSI color is present:
**bold**, `inline code`, and ```code fences``` still render, but block headers (`##`) and
tables show as raw symbols. Coloring skips code, tables, and inline spans, but it cannot
preserve their *structure* in a colored message. Streaming is also suppressed, so colored
messages appear all at once. Use the kill switch if you need clean tables.

## Requirements

Python 3.7+ · [spaCy](https://spacy.io) with `en_core_web_sm` · a 256-color terminal.

## License

MIT — see [LICENSE](LICENSE).
