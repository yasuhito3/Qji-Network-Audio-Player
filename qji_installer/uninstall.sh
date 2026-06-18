#!/bin/bash
# Qji 奏在 アンインストーラー

if [ -z "$TERM" ] || [ "$TERM" = "dumb" ]; then
    xterm -fa "Monospace" -fs 12 -title "Qji アンインストーラー" \
          -geometry 70x25 -e bash "$0" "$@"
    exit $?
fi

QJI_DIR="$HOME/qji"
DESKTOP_DIR="$(xdg-user-dir DESKTOP 2>/dev/null)"
[ -z "$DESKTOP_DIR" ] && DESKTOP_DIR="$HOME/Desktop"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Qji 奏在 アンインストーラー"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "以下を削除します:"
echo "  • ~/qji/ ディレクトリ全体"
echo "  • デスクトップアイコン（3個）"
echo ""
read -rp "本当に削除しますか？ [y/N] " answer
case "$answer" in
    [yY]*)
        rm -rf "$QJI_DIR"
        rm -f "$DESKTOP_DIR/Qji奏在.desktop"
        rm -f "$DESKTOP_DIR/音楽ライブラリー解析.desktop"
        rm -f "$DESKTOP_DIR/オーディオイコライザー.desktop"
        echo ""
        echo "✓ Qji 奏在を削除しました。"
        echo "  設定ファイル（~/.music_player_presets.json 等）は保持されています。"
        ;;
    *)
        echo "キャンセルしました。"
        ;;
esac
echo ""
read -rp "Enterキーで閉じます..." _
