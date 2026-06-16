#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Detect OS
OS="$(uname -s)"
ARCH="$(uname -m)"

show_menu() {
    clear
    echo "=========================================="
    echo "     ONLYSNAP DASHBOARD"
    echo "=========================================="
    echo "1) Run OnlySnap"
    echo "2) Install Requirements"
    echo "3) Install DRM Tools (FFmpeg, MP4Decrypt, RE)"
    echo "4) Add to PATH (use 'onlyfans' / 'patreon' from anywhere)"
    echo ""
    read -p "Select option (1, 2, 3 or 4): " choice
}

# ==========================================
# Option 1: Run OnlySnap
# ==========================================
run_onlysnap() {
    python3 OnlySnap.py
    read -p "Press Enter to continue..."
}

# ==========================================
# Option 2: Install Requirements
# ==========================================
install_requirements() {
    clear
    echo "Installing Python requirements..."
    echo "----------------------------------------"
    pip3 install -r Site/requirements.txt
    echo ""
    echo "Done!"
    read -p "Press Enter to continue..."
}

# ==========================================
# Option 3: Install DRM Tools
# ==========================================
install_drm_tools() {
    clear
    echo "=========================================="
    echo "  INSTALLING DRM TOOLS"
    echo "=========================================="
    echo ""
    echo "  OS:   $OS"
    echo "  Arch: $ARCH"
    echo "=========================================="
    
    mkdir -p Site/dmr

    # --- macOS: auto-install Homebrew if missing ---
    if [ "$OS" = "Darwin" ] && ! command -v brew &>/dev/null; then
        echo ""
        echo "Homebrew not found. Installing..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        # Add to current session
        if [ -f "/opt/homebrew/bin/brew" ]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [ -f "/usr/local/bin/brew" ]; then
            eval "$(/usr/local/bin/brew shellenv)"
        fi
    fi

    # --- FFmpeg ---
    echo ""
    echo "[1/3] Installing FFmpeg..."
    if command -v ffmpeg &>/dev/null; then
        echo "  ✅ FFmpeg already installed: $(ffmpeg -version 2>&1 | head -1)"
    elif [ -f "Site/dmr/ffmpeg" ]; then
        echo "  ✅ FFmpeg already in Site/dmr/"
    else
        if [ "$OS" = "Darwin" ]; then
            echo "  Installing via Homebrew..."
            brew install ffmpeg
        else
            if command -v apt-get &>/dev/null; then
                sudo apt-get update && sudo apt-get install -y ffmpeg
            elif command -v dnf &>/dev/null; then
                sudo dnf install -y ffmpeg
            elif command -v pacman &>/dev/null; then
                sudo pacman -S --noconfirm ffmpeg
            elif command -v apk &>/dev/null; then
                sudo apk add ffmpeg
            else
                echo "  ❌ Could not detect package manager."
                echo "  Install ffmpeg manually for your distro."
            fi
        fi
    fi
    # Symlink to dmr if installed globally
    FFMPEG_PATH="$(command -v ffmpeg 2>/dev/null)"
    if [ -n "$FFMPEG_PATH" ] && [ ! -f "Site/dmr/ffmpeg" ]; then
        ln -sf "$FFMPEG_PATH" "Site/dmr/ffmpeg"
        echo "  Linked: ffmpeg -> Site/dmr/ffmpeg"
    fi

    # --- mp4decrypt (Bento4) ---
    echo ""
    echo "[2/3] Installing mp4decrypt (Bento4)..."
    if [ -f "Site/dmr/mp4decrypt" ]; then
        echo "  ✅ mp4decrypt already in Site/dmr/"
    else
        if [ "$OS" = "Darwin" ]; then
            BENTO4_URL="https://www.bok.net/Bento4/binaries/Bento4-SDK-1-6-0-641.universal-apple-macosx.zip"
        elif [ "$ARCH" = "x86_64" ]; then
            BENTO4_URL="https://www.bok.net/Bento4/binaries/Bento4-SDK-1-6-0-641.x86_64-unknown-linux.zip"
        elif [ "$ARCH" = "aarch64" ]; then
            echo "  ⚠️  No official Bento4 arm64 Linux binary."
            echo "  Try: sudo apt install bento4  or build from source."
            BENTO4_URL=""
        else
            echo "  ❌ Unsupported architecture: $ARCH"
            BENTO4_URL=""
        fi

        if [ -n "$BENTO4_URL" ]; then
            echo "  Downloading from: $BENTO4_URL"
            curl -L -o "/tmp/bento4.zip" "$BENTO4_URL"
            TMP_BENTO="/tmp/bento4_extract"
            rm -rf "$TMP_BENTO"
            mkdir -p "$TMP_BENTO"
            unzip -o "/tmp/bento4.zip" -d "$TMP_BENTO" >/dev/null 2>&1
            MP4D_BIN="$(find "$TMP_BENTO" -name "mp4decrypt" -type f | head -1)"
            if [ -n "$MP4D_BIN" ]; then
                cp "$MP4D_BIN" "Site/dmr/mp4decrypt"
                chmod +x "Site/dmr/mp4decrypt"
                echo "  ✅ mp4decrypt installed!"
            else
                echo "  ❌ Could not find mp4decrypt in archive."
            fi
            rm -rf "$TMP_BENTO" "/tmp/bento4.zip"
        fi
    fi

    # --- N_m3u8DL-RE ---
    echo ""
    echo "[3/3] Installing N_m3u8DL-RE..."
    if [ -f "Site/dmr/N_m3u8DL-RE" ]; then
        echo "  ✅ N_m3u8DL-RE already in Site/dmr/"
    else
        RE_URL=""
        if [ "$OS" = "Darwin" ]; then
            if [ "$ARCH" = "arm64" ]; then
                RE_URL="https://github.com/nilaoda/N_m3u8DL-RE/releases/download/v0.5.1-beta/N_m3u8DL-RE_v0.5.1-beta_osx-arm64_20251029.tar.gz"
            else
                RE_URL="https://github.com/nilaoda/N_m3u8DL-RE/releases/download/v0.5.1-beta/N_m3u8DL-RE_v0.5.1-beta_osx-x64_20251029.tar.gz"
            fi
        else
            if [ "$ARCH" = "x86_64" ]; then
                RE_URL="https://github.com/nilaoda/N_m3u8DL-RE/releases/download/v0.5.1-beta/N_m3u8DL-RE_v0.5.1-beta_linux-x64_20251029.tar.gz"
            elif [ "$ARCH" = "aarch64" ]; then
                RE_URL="https://github.com/nilaoda/N_m3u8DL-RE/releases/download/v0.5.1-beta/N_m3u8DL-RE_v0.5.1-beta_linux-arm64_20251029.tar.gz"
            else
                echo "  ❌ Unsupported architecture: $ARCH"
            fi
        fi

        if [ -n "$RE_URL" ]; then
            echo "  Downloading from: $RE_URL"
            curl -L -o "/tmp/n_m3u8dl.tar.gz" "$RE_URL"
            tar -xzf "/tmp/n_m3u8dl.tar.gz" -C "Site/dmr/" 2>/dev/null
            rm -f "/tmp/n_m3u8dl.tar.gz"
            if [ -f "Site/dmr/N_m3u8DL-RE" ]; then
                chmod +x "Site/dmr/N_m3u8DL-RE"
                echo "  ✅ N_m3u8DL-RE installed!"
            else
                echo "  ❌ N_m3u8DL-RE download/extract failed."
            fi
        fi
    fi

    echo ""
    echo "=========================================="
    echo "  STATUS:"
    if [ -f "Site/dmr/ffmpeg" ] || command -v ffmpeg &>/dev/null; then
        echo "  FFmpeg:       ✅ OK"
    else
        echo "  FFmpeg:       ❌ MISSING"
    fi
    if [ -f "Site/dmr/mp4decrypt" ]; then
        echo "  mp4decrypt:   ✅ OK"
    else
        echo "  mp4decrypt:   ❌ MISSING"
    fi
    if [ -f "Site/dmr/N_m3u8DL-RE" ]; then
        echo "  N_m3u8DL-RE:  ✅ OK"
    else
        echo "  N_m3u8DL-RE:  ❌ MISSING"
    fi
    echo "=========================================="
    read -p "Press Enter to continue..."
}

# ==========================================
# Option 4: Add to PATH
# ==========================================
add_to_path() {
    clear
    echo "=========================================="
    echo "  ADD ONLYSNAP COMMANDS TO PATH"
    echo "=========================================="
    echo ""
    echo "This will create 'onlyfans' and 'patreon' commands"
    echo "that work from ANY folder, ANY drive."
    echo ""
    echo "If you move OnlySnap, just run this option again!"
    echo "=========================================="
    echo ""

    BIN_DIR="$HOME/.onlysnap/bin"
    SITE_DIR="$SCRIPT_DIR/Site"

    mkdir -p "$BIN_DIR"

    # Create onlyfans command
    cat > "$BIN_DIR/onlyfans" << EOF
#!/bin/bash
cd "$SITE_DIR"
python3 "$SITE_DIR/OnlyFans.py" "\$@"
EOF
    chmod +x "$BIN_DIR/onlyfans"
    echo "Created: onlyfans"

    # Create patreon command
    cat > "$BIN_DIR/patreon" << EOF
#!/bin/bash
cd "$SITE_DIR"
python3 "$SITE_DIR/Patreon.py" "\$@"
EOF
    chmod +x "$BIN_DIR/patreon"
    echo "Created: patreon"

    # Create onlysnap command
    cat > "$BIN_DIR/onlysnap" << EOF
#!/bin/bash
cd "$SCRIPT_DIR"
python3 "$SCRIPT_DIR/OnlySnap.py" "\$@"
EOF
    chmod +x "$BIN_DIR/onlysnap"
    echo "Created: onlysnap"

    if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
        echo ""
        echo "Adding $BIN_DIR to PATH..."

        SHELL_NAME="$(basename "$SHELL")"
        if [ "$SHELL_NAME" = "zsh" ]; then
            RC_FILE="$HOME/.zshrc"
        elif [ "$SHELL_NAME" = "fish" ]; then
            RC_FILE="$HOME/.config/fish/config.fish"
        else
            RC_FILE="$HOME/.bashrc"
        fi

        PATH_LINE="export PATH=\"\$HOME/.onlysnap/bin:\$PATH\""
        if [ "$SHELL_NAME" = "fish" ]; then
            PATH_LINE="set -gx PATH \$HOME/.onlysnap/bin \$PATH"
        fi

        if ! grep -q ".onlysnap/bin" "$RC_FILE" 2>/dev/null; then
            echo "" >> "$RC_FILE"
            echo "# OnlySnap PATH" >> "$RC_FILE"
            echo "$PATH_LINE" >> "$RC_FILE"
            echo "Added to $RC_FILE"
        else
            echo "PATH already configured in $RC_FILE"
        fi

        # Apply now
        export PATH="$BIN_DIR:$PATH"
    else
        echo ""
        echo "PATH already contains OnlySnap bin folder."
    fi

    echo ""
    echo "=========================================="
    echo "  DONE! Commands registered:"
    echo ""
    echo "  onlyfans   - Launch OnlyFans scraper"
    echo "  patreon    - Launch Patreon scraper"
    echo "  onlysnap   - Launch OnlySnap Hub"
    echo ""
    echo "  Open a NEW terminal to use them."
    echo "  If you move the folder, run option 4 again."
    echo "=========================================="
    read -p "Press Enter to continue..."
}

# ==========================================
# Main Loop
# ==========================================
while true; do
    show_menu
    case $choice in
        1) run_onlysnap ;;
        2) install_requirements ;;
        3) install_drm_tools ;;
        4) add_to_path ;;
        *) echo "Invalid option." ; sleep 1 ;;
    esac
done
