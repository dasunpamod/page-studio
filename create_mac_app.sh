#!/bin/bash
# PageStudio macOS .app Bundle Generator
# Run this once on macOS to generate a native PageStudio.app that can sit in your Applications or Dock.

DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$DIR/PageStudio.app"
CONTENTS_DIR="$APP_DIR/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

echo "Creating PageStudio.app at: $APP_DIR"
mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR"

# Write Info.plist
cat << 'EOF' > "$CONTENTS_DIR/Info.plist"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>PageStudio</string>
    <key>CFBundleIdentifier</key>
    <string>com.pagestudio.ide</string>
    <key>CFBundleName</key>
    <string>PageStudio</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>2.0.0</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.13</string>
    <key>NSHighResolutionCapable</key>
    <true/>
</dict>
</plist>
EOF

# Write executable launcher script inside .app bundle
cat << 'EOF' > "$MACOS_DIR/PageStudio"
#!/bin/bash
DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$DIR"

if command -v python3 >/dev/null 2>&1; then
    exec python3 "$DIR/main.py"
elif [ -x "/opt/homebrew/bin/python3" ]; then
    exec /opt/homebrew/bin/python3 "$DIR/main.py"
elif [ -x "/usr/local/bin/python3" ]; then
    exec /usr/local/bin/python3 "$DIR/main.py"
elif command -v python >/dev/null 2>&1; then
    exec python "$DIR/main.py"
else
    osascript -e 'display alert "Python 3 Not Found" message "Please install Python 3 to run PageStudio."'
    exit 1
fi
EOF

chmod +x "$MACOS_DIR/PageStudio"
chmod +x "$DIR/PageStudio.command"

echo "SUCCESS: PageStudio.app created!"
echo "You can now drag PageStudio.app directly to your Applications folder, Desktop, or Dock."
