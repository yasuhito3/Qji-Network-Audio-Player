#!/bin/bash
# ============================================================
# Qji 奏在 — BubbleUPnP Server セットアップ
# ============================================================

if [ -z "$TERM" ] || [ "$TERM" = "dumb" ]; then
    for _t in xfce4-terminal lxterminal mate-terminal xterm gnome-terminal konsole qterminal; do
        command -v "$_t" &>/dev/null && break
    done
    case "$_t" in
        xfce4-terminal) exec "$_t" --disable-server -T "BubbleUPnP Server セットアップ" -x bash "$0" "$@" ;;
        gnome-terminal) exec "$_t" --title "BubbleUPnP Server セットアップ" -- bash "$0" "$@" ;;
        *)              exec "$_t" -T "BubbleUPnP Server セットアップ" -e bash "$0" "$@" ;;
    esac
    exit $?
fi

DEB_URL="https://bubblesoftapps.com/bubbleupnpserver/bubbleupnpserver_0.9-8_all.deb"
DEB_FILE="/tmp/bubbleupnpserver.deb"
BUBBLE_PORT=58050

clear
echo "╔══════════════════════════════════════════════════╗"
echo "║   📡 BubbleUPnP Server セットアップ               ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "  公式サイト: https://bubblesoftapps.com/bubbleupnpserver2/"
echo "  インストール方法: debパッケージ（apt）"
echo "  ポート: $BUBBLE_PORT"
echo ""
echo "──────────────────────────────────────────────────"

# --- 既存の旧PPA版を削除（存在する場合） ---
if dpkg -l | grep -q "bubbleupnpserver" 2>/dev/null; then
    echo ""
    echo "▶ 既存のBubbleUPnP Serverを確認中..."
    OLD_VER=$(dpkg -l bubbleupnpserver 2>/dev/null | grep "^ii" | awk '{print $3}')
    echo "  インストール済み: $OLD_VER"
    read -rp "  再インストールしますか？ [y/N] " reinstall
    [[ "$reinstall" =~ ^[yY] ]] || { echo "  スキップします。"; read -rp "Enterで閉じます..." _; exit 0; }
fi

# --- ダウンロード ---
echo ""
echo "▶ BubbleUPnP Server をダウンロード中..."
echo "  $DEB_URL"
echo ""

if command -v wget &>/dev/null; then
    wget -q --show-progress -O "$DEB_FILE" "$DEB_URL"
elif command -v curl &>/dev/null; then
    curl -L --progress-bar -o "$DEB_FILE" "$DEB_URL"
else
    echo "❌ wget/curl が見つかりません。"
    read -rp "Enterで閉じます..." _; exit 1
fi

if [ ! -f "$DEB_FILE" ]; then
    echo ""
    echo "❌ ダウンロードに失敗しました。"
    echo "   ネットワーク接続を確認するか、手動でインストールしてください:"
    echo "   $DEB_URL"
    read -rp "Enterで閉じます..." _; exit 1
fi

# --- インストール ---
echo ""
echo "▶ インストール中..."
sudo apt-get install -y "$DEB_FILE"
rm -f "$DEB_FILE"

if ! command -v bubbleupnpserver &>/dev/null && \
   ! systemctl list-units --all | grep -q bubbleupnp 2>/dev/null; then
    echo ""
    echo "❌ インストールに失敗しました。"
    read -rp "Enterで閉じます..." _; exit 1
fi

# --- UFWポート開放 ---
if command -v ufw &>/dev/null; then
    echo ""
    echo "▶ ファイアウォール設定..."
    sudo ufw allow "$BUBBLE_PORT/tcp" >/dev/null 2>&1
    echo "  ✓ ポート $BUBBLE_PORT を開放しました"
fi

# --- 完了 ---
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ BubbleUPnP Server のインストールが完了しました！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  設定画面: http://localhost:$BUBBLE_PORT"
echo ""
echo "  【初回セットアップ手順】"
echo "  1. デスクトップの「📡 gmediarenderレシーバー」を先に起動"
echo "  2. ブラウザで http://localhost:$BUBBLE_PORT を開く"
echo "  3. 「Devices」タブで「Qji Player」が表示されることを確認"
echo "  4. スマホに「BubbleUPnP」アプリをインストール"
echo "  5. アプリ設定でサーバーアドレスを入力:"
echo "       http://$(hostname -I | awk '{print $1}'):$BUBBLE_PORT"
echo "  6. レンダラーとして「Qji Player」を選択して再生"
echo ""
echo "  詳細: https://bubblesoftapps.com/bubbleupnpserver2/docs/linux_install.html"
echo ""

# --- サービス起動確認 ---
if systemctl is-active --quiet bubbleupnpserver 2>/dev/null; then
    echo "  ✓ BubbleUPnP Server は既に起動中です"
else
    read -rp "今すぐ BubbleUPnP Server を起動しますか？ [Y/n] " launch
    case "$launch" in
        [nN]*) ;;
        *) sudo systemctl start bubbleupnpserver 2>/dev/null || \
           sudo service bubbleupnpserver start 2>/dev/null
           echo "  ✓ 起動しました"
           ;;
    esac
fi

echo ""
read -rp "Enterで閉じます..." _
