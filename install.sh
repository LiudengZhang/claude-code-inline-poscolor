#!/usr/bin/env bash
# Installer for claude-code-inline-poscolor.
#   - ensures spaCy + the en_core_web_sm model are present
#   - registers the MessageDisplay hook in ~/.claude/settings.json (merged, not clobbered)
#   - makes the scripts executable
# Re-runnable and idempotent. Fails cleanly with a clear message.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="${HOME}/.claude"
SETTINGS="${CLAUDE_DIR}/settings.json"
HOOK="${REPO}/src/messagedisplay_hook.py"

echo "==> repo:     ${REPO}"
echo "==> settings: ${SETTINGS}"

command -v python3 >/dev/null 2>&1 || { echo "ERROR: python3 not found"; exit 1; }

echo "==> checking spaCy + en_core_web_sm"
python3 - <<'PY'
import importlib, sys, subprocess
try:
    import spacy  # noqa
except ImportError:
    print("ERROR: spaCy not installed. Run:  pip install spacy", file=sys.stderr)
    sys.exit(1)
import spacy
try:
    spacy.load("en_core_web_sm")
except Exception:
    print("    model missing -> downloading en_core_web_sm")
    subprocess.check_call([sys.executable, "-m", "spacy", "download", "en_core_web_sm"])
print("    spaCy OK")
PY

echo "==> making scripts executable"
chmod +x "${HOOK}" "${REPO}/src/mdcolor_daemon.py" "${REPO}/bin/pos-color" "${REPO}/bin/colorize"

echo "==> registering MessageDisplay hook in settings.json"
mkdir -p "${CLAUDE_DIR}"
HOOK="${HOOK}" SETTINGS="${SETTINGS}" python3 - <<'PY'
import json, os
settings_path = os.environ["SETTINGS"]
hook = os.environ["HOOK"]
try:
    with open(settings_path) as f:
        cfg = json.load(f)
except FileNotFoundError:
    cfg = {}
cfg.setdefault("hooks", {})
entry = {"type": "command", "command": f"python3 {hook}"}
md = cfg["hooks"].setdefault("MessageDisplay", [{"hooks": []}])
group = md[0].setdefault("hooks", [])
# replace any prior install of this hook, else append
group[:] = [h for h in group if "messagedisplay_hook.py" not in h.get("command", "")]
group.append(entry)
with open(settings_path, "w") as f:
    json.dump(cfg, f, indent=2)
print("    hook registered")
PY

echo
echo "Done. Coloring is now ON for new Claude Code sessions."
echo "  disable:  touch ${CLAUDE_DIR}/mdcolor_off"
echo "  enable:   rm -f ${CLAUDE_DIR}/mdcolor_off"
echo "  on-demand tools:  ${REPO}/bin/pos-color  and  ${REPO}/bin/colorize"
