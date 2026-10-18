#!/bin/bash
# PageStudio macOS Launcher
# Double-click this file in Finder to launch PageStudio without opening Terminal manually.

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Find python3 on macOS (Homebrew, python.org, or Xcode CLI tools)
if command -v python3 >/dev/null 2>&1; then
    exec python3 "$DIR/main.py" "$@"
elif [ -x "/usr/local/bin/python3" ]; then
    exec /usr/local/bin/python3 "$DIR/main.py" "$@"
elif [ -x "/opt/homebrew/bin/python3" ]; then
    exec /opt/homebrew/bin/python3 "$DIR/main.py" "$@"
elif command -v python >/dev/null 2>&1; then
    exec python "$DIR/main.py" "$@"
else
    osascript -e 'display alert "Python 3 Not Found" message "Please install Python 3 to run PageStudio on macOS."'
    exit 1
fi
