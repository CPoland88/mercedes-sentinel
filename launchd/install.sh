#!/bin/bash
# Mercedes Sentinel — launchd install script (C3).
#
# Copies the plist into ~/Library/LaunchAgents/, loads it via
# launchctl bootstrap, creates the log directory, and prints the
# one remaining manual step (pmset wake schedule).
#
# Idempotent — safe to re-run after editing the plist.

set -euo pipefail

PLIST_NAME="com.craigpoland.mercedes-sentinel.plist"
SOURCE_PLIST="$(cd "$(dirname "$0")" && pwd)/$PLIST_NAME"
DEST_DIR="$HOME/Library/LaunchAgents"
DEST_PLIST="$DEST_DIR/$PLIST_NAME"
LOG_DIR="$HOME/Library/Logs/MercedesSentinel"
UID_NUM="$(id -u)"

echo "Mercedes Sentinel — launchd installer"
echo "======================================"
echo ""

if [ ! -f "$SOURCE_PLIST" ]; then
    echo "ERROR: source plist not found at $SOURCE_PLIST"
    exit 1
fi

mkdir -p "$DEST_DIR"
mkdir -p "$LOG_DIR"

# If a previous version is already loaded, bootout first so the copy
# can replace it cleanly.
if [ -f "$DEST_PLIST" ]; then
    echo "Existing plist found at $DEST_PLIST"
    echo "Unloading the previous version..."
    launchctl bootout "gui/$UID_NUM" "$DEST_PLIST" 2>/dev/null || true
fi

cp "$SOURCE_PLIST" "$DEST_PLIST"
echo "Copied plist -> $DEST_PLIST"

launchctl bootstrap "gui/$UID_NUM" "$DEST_PLIST"
echo "Loaded into launchd."
echo ""

echo "Verification:"
if launchctl list | grep -q "com.craigpoland.mercedes-sentinel"; then
    echo "  launchctl list confirms the job is loaded."
else
    echo "  WARNING: launchctl list did NOT show the job. Investigate."
fi

echo ""
echo "Log destination: $LOG_DIR/run.log"
echo "  tail -f \"$LOG_DIR/run.log\"   to watch the next run"
echo ""

echo "======================================"
echo "One manual step remains: enable scheduled wake-from-sleep."
echo "======================================"
echo ""
echo "By default the plist only runs if the Mac is awake at 4 PM."
echo "To make sure the Mac wakes up first, run (will prompt for password):"
echo ""
echo "  sudo pmset repeat wakeorpoweron MTWRFSU 15:55:00"
echo ""
echo "That wakes the machine at 3:55 PM every day, 5 min before launchd"
echo "fires at 4:00 PM. The 5-min headroom ensures network / DNS / etc."
echo "are fully up before the job tries to run."
echo ""
echo "Verify with:  pmset -g sched"
echo "Cancel with:  sudo pmset repeat cancel"
echo ""
echo "To test the schedule without waiting until 4 PM tomorrow, run:"
echo ""
echo "  launchctl kickstart gui/\$UID/com.craigpoland.mercedes-sentinel"
echo ""
echo "That triggers the job immediately, and you should receive the daily"
echo "summary email within ~30 seconds (assuming Anthropic API + Gmail SMTP"
echo "are reachable)."
