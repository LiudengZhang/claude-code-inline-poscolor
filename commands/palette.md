---
description: Show or switch the POS-color palette
argument-hint: [cyan-orange|pink-green|gold-purple|blue-yellow|teal-magenta]
allowed-tools: Bash
---

Set the active palette to "$ARGUMENTS" (or list the choices if empty), then report the result.

!`p="$ARGUMENTS"; valid="cyan-orange pink-green gold-purple blue-yellow teal-magenta"; f=~/.claude/mdcolor_palette; if [ -z "$p" ]; then echo "current: $(cat $f 2>/dev/null || echo cyan-orange)"; echo "choices: $valid"; elif echo " $valid " | grep -q " $p "; then echo "$p" > $f; echo "palette set to $p (instant, no restart)"; else echo "unknown palette: $p"; echo "choices: $valid"; fi`
