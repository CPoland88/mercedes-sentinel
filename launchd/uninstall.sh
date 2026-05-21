#!/bin/bash
# Mercedes Sentinel — launchd uninstall script (C3).
#
# Symmetric counterpart to install.sh: stops the job, removes the
# plist, leaves logs and data intact (delete those manually if you
# really want to wipe state).

set -euo pipefail

PLIST_NAME="com.craigpoland.mercedes-sentinel.plist"
DEST_PLIST="$HOME/Library/LaunchAgents/$PLIST_NAME"
UID_NUM="$(id -u)"

echo "Mercedes Sentinel — launchd uninstaller"
echo "========================================"
echo ""

if [ -f "$DEST_PLIST" ]; then
    echo "Unloading job from launchd..."
    launchctl bootout "gui/$UID_NUM" "$DEST_PLIST" 2>/dev/null || true
    echo "Removing plist..."
    rm -f "$DEST_PLIST"
    echo "Removed: $DEST_PLIST"
else
    echo "No plist found at $DEST_PLIST — nothing to uninstall."
fi

echo ""
echo "Logs at ~/Library/Logs/MercedesSentinel/ left intact."
echo "Data at <repo>/data/ left intact."
echo ""
echo "If you also want to disable scheduled wake-from-sleep:"
echo "  sudo pmset repeat cancel"
