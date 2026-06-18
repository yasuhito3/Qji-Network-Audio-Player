#!/bin/bash
# ============================================================
# Qji 奏在 — インストーラー起動ブートストラップ
#  %k 等のデスクトップ変数に依存せず install.sh を探索して実行
# ============================================================

if [ -z "$TERM" ] || [ "$TERM" = "dumb" ]; then
    for _t in xfce4-terminal lxterminal mate-terminal xterm gnome-terminal konsole qterminal; do
        command -v "$_t" &>/dev/null && break
    done
    case "$_t" in
        xfce4-terminal) exec "$_t" --disable-server -T "Qji インストーラー" -x bash "$0" "$@" ;;
        gnome-terminal) exec "$_t" --title "Qji インストーラー" -- bash "$0" "$@" ;;
        *)              exec "$_t" -T "Qji インストーラー" -e bash "$0" "$@" ;;
    esac
    exit $?
fi

# 1. このスクリプト自身と同じディレクトリを最優先
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
if [ -f "$SELF_DIR/install.sh" ]; then
    cd "$SELF_DIR"
    exec bash install.sh
fi

# 2. よくあるダウンロード先からqji_installerフォルダを探索
echo "install.sh を検索しています..."
for base in "$HOME" "$(xdg-user-dir DOWNLOAD 2>/dev/null)" "$HOME/Downloads" "$HOME/ダウンロード" "$HOME/Desktop" "$(xdg-user-dir DESKTOP 2>/dev/null)"; do
    [ -z "$base" ] && continue
    found=$(find "$base" -maxdepth 5 -type f -iname "install.sh" -path "*[Qq]ji_installer*" 2>/dev/null | head -1)
    if [ -n "$found" ]; then
        cd "$(dirname "$found")"
        exec bash install.sh
    fi
done

echo ""
echo "❌ install.sh が見つかりませんでした。"
echo "   このファイルを Qji_installer フォルダの中に置いて"
echo "   再度実行してください。"
echo ""
read -rp "Enterで閉じます..." _
