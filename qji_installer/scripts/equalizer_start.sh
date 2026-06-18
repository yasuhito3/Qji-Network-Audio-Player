#!/bin/bash
# ============================================================
# Qji 奏在 — オーディオイコライザー起動ラッパー
#  tkinter未導入時のみターミナルを表示して案内・自動インストール
# ============================================================

QJI_DIR="$HOME/qji"
LOG_FILE="/tmp/qji_equalizer_error.log"

cd "$QJI_DIR" || exit 1

open_terminal_and_run() {
    # tkinter未導入/起動失敗時のみ、ターミナルを自前で開いて表示する
    local script="$1"
    for _t in xfce4-terminal lxterminal mate-terminal xterm gnome-terminal konsole qterminal; do
        command -v "$_t" &>/dev/null && break
    done
    case "$_t" in
        xfce4-terminal) exec "$_t" --disable-server -T "🎚️ オーディオイコライザー" -x bash "$script" ;;
        gnome-terminal) exec "$_t" --title "🎚️ オーディオイコライザー" -- bash "$script" ;;
        *)              exec "$_t" -T "🎚️ オーディオイコライザー" -e bash "$script" ;;
    esac
}

# tkinter の存在確認（ターミナルなしの状態でチェック）
if ! python3 -c "import tkinter" 2>/dev/null; then
    # この時点ではターミナルが無いので、案内表示用の別スクリプトを作って
    # ターミナル経由で実行する
    HELPER="/tmp/qji_tk_setup.sh"
    cat > "$HELPER" << 'HELPEREOF'
#!/bin/bash
clear
echo "╔══════════════════════════════════════════════════╗"
echo "║   🎚️  オーディオイコライザー                      ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "  ⚠ tkinter（GUI表示ライブラリ）が見つかりません。"
echo "    自動インストールを試みます..."
echo ""

if command -v apt-get &>/dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y python3-tk
fi

if ! python3 -c "import tkinter" 2>/dev/null; then
    echo ""
    echo "  ❌ 自動インストールに失敗しました。"
    echo "    お使いのディストリビューションに応じて、"
    echo "    以下のいずれかを試してください:"
    echo ""
    echo "      Debian/Ubuntu系:  sudo apt install python3-tk"
    echo "      Fedora系:         sudo dnf install python3-tkinter"
    echo "      Arch系:           sudo pacman -S tk"
    echo ""
    read -rp "Enterで閉じます..." _
    exit 1
fi

echo ""
echo "  ✓ tkinter のインストールに成功しました。起動します..."
sleep 1
HELPEREOF
    chmod +x "$HELPER"
    open_terminal_and_run "$HELPER"
    # ここに到達するのはターミナルが見つからなかった場合のみ
    bash "$HELPER"
fi

# tkinter OK → ターミナルなしで直接GUI起動
python3 audio_equalizer.py 2>>"$LOG_FILE"
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    HELPER2="/tmp/qji_eq_error.sh"
    cat > "$HELPER2" << HELPEREOF2
#!/bin/bash
clear
echo "❌ オーディオイコライザーの起動中にエラーが発生しました。"
echo "──────────────────────────────────────────"
tail -n 30 "$LOG_FILE"
echo "──────────────────────────────────────────"
read -rp "Enterで閉じます..." _
HELPEREOF2
    chmod +x "$HELPER2"
    open_terminal_and_run "$HELPER2"
    bash "$HELPER2"
fi
