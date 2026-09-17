#!/usr/bin/env bash
# install-acs.sh — the user side of agent-control-shell. NO ROOT: symlinks into ~/.local/bin
# and an autostart entry for the tray. The root side (mrog-lease, mrog-apply, policy, the
# kill helper) is installed separately by its own `sudo bash` pastes — see INSTALL.md.
#
#   bash install-acs.sh            # symlink acs + acs-tray, autostart the tray
#   bash install-acs.sh --no-tray  # symlink only
#   bash install-acs.sh --remove
set -euo pipefail
[[ $EUID -ne 0 ]] || { echo "do NOT run as root - this installs into your own session"; exit 1; }
SRC="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
BIN="$HOME/.local/bin"; AUTO="$HOME/.config/autostart/acs-tray.desktop"

if [ "${1:-}" = --remove ]; then
  pkill -f "$SRC/acs-tray.py" 2>/dev/null || true
  rm -f "$BIN/acs" "$BIN/acs-tray" "$AUTO"; echo "removed acs, acs-tray, autostart"; exit 0
fi
install -d "$BIN" "$(dirname "$AUTO")"
# Symlinks, not copies: a copy here would shadow the source forever (the askpill lesson).
ln -sfn "$SRC/acs" "$BIN/acs"
ln -sfn "$SRC/acs-tray.py" "$BIN/acs-tray"
echo "linked: $BIN/acs -> $SRC/acs ; $BIN/acs-tray -> $SRC/acs-tray.py"
[ "${1:-}" = --no-tray ] && exit 0
cat > "$AUTO" <<EOF
[Desktop Entry]
Type=Application
Name=agent-control-shell tray
Comment=Lease state for the agent root shell; grant, end, journal
Exec=$BIN/acs-tray
Icon=security-medium
X-GNOME-Autostart-enabled=true
OnlyShowIn=X-Cinnamon;XFCE;MATE;LXQt;GNOME;
EOF
echo "autostart: $AUTO"
# Start it now unless one is already running for this display.
if ! pgrep -f "$SRC/acs-tray.py" >/dev/null 2>&1; then
  setsid nohup "$BIN/acs-tray" >/dev/null 2>&1 & disown
  sleep 1; pgrep -f "$SRC/acs-tray.py" >/dev/null && echo "tray: running (pid $(pgrep -f "$SRC/acs-tray.py" | head -1))" || echo "tray: did not start - run $BIN/acs-tray in a terminal to see why"
else
  echo "tray: already running"
fi
echo; echo "Prove it:  acs status   |   acs status --format waybar   |   look for the dot in your tray"
