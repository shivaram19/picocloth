#!/bin/bash
# VNC Server Setup for LinkedIn Bot
# Run this to start a virtual display that you can connect to via VNC

set -e

DISPLAY_NUM=1
VNC_PORT=$((5900 + DISPLAY_NUM))
WIDTH=1920
HEIGHT=1080
DEPTH=24

echo "=========================================="
echo "LinkedIn Bot — VNC Display Setup"
echo "=========================================="

# Check if tightvncserver is installed
if ! command -v tightvncserver &> /dev/null; then
    echo "Installing tightvncserver..."
    sudo apt-get update && sudo apt-get install -y tightvncserver xfce4 xfce4-terminal
fi

# Check if Xvfb is available
if ! command -v Xvfb &> /dev/null; then
    echo "Installing Xvfb..."
    sudo apt-get install -y xvfb
fi

# Kill existing VNC sessions on this display
vncserver -kill :$DISPLAY_NUM 2>/dev/null || true
pkill -f "Xvfb :$DISPLAY_NUM" 2>/dev/null || true
sleep 1

# Start Xvfb (virtual framebuffer)
echo "Starting virtual display :$DISPLAY_NUM (${WIDTH}x${HEIGHT}x${DEPTH})..."
Xvfb :$DISPLAY_NUM -screen 0 ${WIDTH}x${HEIGHT}x${DEPTH} +extension RANDR &
XVFB_PID=$!
sleep 2

# Export display for applications
export DISPLAY=:$DISPLAY_NUM

# Start a simple window manager
if command -v fluxbox &> /dev/null; then
    fluxbox &
elif command -v openbox &> /dev/null; then
    openbox &
fi

echo ""
echo "=========================================="
echo "✅ Virtual display ready!"
echo "=========================================="
echo "Display: :$DISPLAY_NUM"
echo ""
echo "To run the LinkedIn bot WITH visible browser:"
echo ""
echo "  export DISPLAY=:$DISPLAY_NUM"
echo "  python3 outreach_bot_v2.py --limit 2 --no-headless"
echo ""
echo "The browser will render on display :$DISPLAY_NUM"
echo ""
echo "To VIEW the browser remotely, you have 3 options:"
echo ""
echo "--- OPTION 1: VNC (recommended) ---"
echo "Start VNC server on the display:"
echo "  x11vnc -display :$DISPLAY_NUM -rfbport $VNC_PORT -forever -shared &"
echo "Then connect from your local machine:"
echo "  vncviewer <server-ip>:$VNC_PORT"
echo ""
echo "--- OPTION 2: Screenshot viewer ---"
echo "The bot auto-saves screenshots to screenshots/"
echo "View them with: ls -la screenshots/"
echo ""
echo "--- OPTION 3: X11 forwarding (if using SSH -X) ---"
echo "Not available in current session (no X11 forwarding)"
echo ""
echo "Press Ctrl+C to stop the virtual display"
echo "=========================================="

# Keep the script running
wait $XVFB_PID
