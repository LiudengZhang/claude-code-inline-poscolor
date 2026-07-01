---
description: Toggle inline POS coloring on/off
allowed-tools: Bash
---

Flip the coloring kill-switch (`~/.claude/mdcolor_off`) and report the new state.

!`if [ -f ~/.claude/mdcolor_off ]; then rm -f ~/.claude/mdcolor_off; echo "poscolor: ON"; else touch ~/.claude/mdcolor_off; echo "poscolor: OFF"; fi`
