---
description: Show or change the spaCy tagger model (reloads the daemon)
argument-hint: [en_core_web_sm|en_core_web_md|en_core_web_trf]
allowed-tools: Bash
---

Set the tagger model to "$ARGUMENTS" (or show the current one if empty), then report the result.

!`m="$ARGUMENTS"; f=~/.claude/mdcolor_model; if [ -z "$m" ]; then echo "current: $(cat $f 2>/dev/null || echo en_core_web_sm)"; else echo "$m" > $f; pkill -f mdcolor_daemon.py 2>/dev/null; echo "model set to $m; daemon reloads on the next message"; fi`
