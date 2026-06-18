#!/bin/bash
# ============================================================
# Qji 奏在 — 起動ラッパー
# ============================================================

QJI_DIR="$HOME/qji"
MARKER="$HOME/.qji_library_scanned"

clear

# ── 音楽フォルダの存在確認 ──────────────────────────────
MUSIC_XDG="$(xdg-user-dir MUSIC 2>/dev/null)"
QJI_USER="${USER:-$(whoami)}"
HAS_MUSIC=0
for d in "$MUSIC_XDG" "$HOME/Music" "$HOME/ミュージック" \
          "/run/media/$QJI_USER" "/media/$QJI_USER" "/mnt"; do
    [ -d "$d" ] && [ "$(ls -A "$d" 2>/dev/null)" ] && HAS_MUSIC=1 && break
done

if [ ! -f "$MARKER" ]; then
    echo "╔══════════════════════════════════════════════════╗"
    echo "║              🎵 Qji 奏在                          ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo ""
    if [ "$HAS_MUSIC" -eq 0 ]; then
        echo "  ⚠ 音楽フォルダが見つかりませんでした。"
        echo "    音源フォルダを用意してから"
        echo "    「①音源ライブラリー構築」を実行してください。"
        echo ""
        echo "    音楽フォルダの場所: $MUSIC_XDG"
        echo "    （または /run/media/$QJI_USER/ 以下のマウント済みドライブ）"
        echo ""
    else
        echo "  音源ライブラリーDB（~/music_mood_db.json）が"
        echo "  まだ構築されていないようです。"
        echo ""
        echo "  デスクトップの"
        echo "    🗄 ①音源ライブラリー構築"
        echo "  を先に実行しておくと、ジャンル/ムード判定の精度が"
        echo "  上がり、ランダム再生がスムーズになります。"
        echo ""
    fi
    echo "  （構築せずにこのまま使うこともできます）"
    echo ""
    read -rp "  このまま Qji を起動しますか？ [Y/n] " ans
    case "$ans" in
        [nN]*) exit 0 ;;
    esac
    clear
fi

cd "$QJI_DIR" || exit 1

# ── 起動ロゴを全画面表示（feh がある場合のみ）────────────────
LOGO="$QJI_DIR/icons/qji_logo.png"
if command -v feh &>/dev/null && [ -f "$LOGO" ]; then
    feh --fullscreen --hide-pointer --no-menus \
        --title "QjiLogo" "$LOGO" &
    FEH_PID=$!
    sleep 3
    kill "$FEH_PID" 2>/dev/null
    wait "$FEH_PID" 2>/dev/null
fi

python3 qji.py
echo ""
echo "Qji を終了しました。Enterキーで閉じます..."
read -r _
