#!/bin/bash
# ============================================================
# Qji 奏在 — ネットワークポート開放スクリプト
# AirPlay (shairport-sync) / gmediarender (UPnP-DLNA) 用
# ============================================================

if [ -z "$TERM" ] || [ "$TERM" = "dumb" ]; then
    for _t in xfce4-terminal lxterminal mate-terminal xterm gnome-terminal konsole qterminal; do
        command -v "$_t" &>/dev/null && break
    done
    case "$_t" in
        xfce4-terminal) exec "$_t" --disable-server -T "🌐 ネットワーク設定" -x bash "$0" "$@" ;;
        gnome-terminal) exec "$_t" --title "🌐 ネットワーク設定" -- bash "$0" "$@" ;;
        *)              exec "$_t" -T "🌐 ネットワーク設定" -e bash "$0" "$@" ;;
    esac
    exit $?
fi

trap 'ec=$?; echo ""; echo "エラー（終了コード: $ec）。Enterで閉じます..."; read _; exit 1' ERR

echo "╔══════════════════════════════════════════╗"
echo "║   Qji 奏在 — ネットワークポート開放        ║"
echo "╚══════════════════════════════════════════╝"
echo ""

if ! command -v ufw &>/dev/null; then
    echo "ufw が見つかりません。インストールします..."
    sudo apt-get update -qq && sudo apt-get install -y ufw
fi

echo "対象ネットワーク（ローカルLANのみ許可）:"
read -rp "  サブネット [192.168.0.0/16]: " SUBNET
SUBNET="${SUBNET:-192.168.0.0/16}"
echo ""

# ------------------------------------------------------------
# 用途別ポート定義
# ------------------------------------------------------------
declare -A AIRPLAY_PORTS=(
    ["5353/udp"]="mDNS / Bonjour（機器検出）"
    ["7000/tcp"]="RTSP（AirPlay制御）"
    ["319/udp"]="PTP タイミング（AirPlay2）"
    ["320/udp"]="PTP タイミング（AirPlay2）"
    ["6000:6009/udp"]="音声/制御/タイミング（shairport-sync）"
)

declare -A DLNA_PORTS=(
    ["1900/udp"]="SSDP（UPnP機器探索）"
    ["49152:49999/tcp"]="gmediarender 動的HTTPポート"
    ["49152:49999/udp"]="gmediarender 動的ポート"
)

echo "▶ AirPlay (shairport-sync) 用ポート"
for port in "${!AIRPLAY_PORTS[@]}"; do
    echo "  - $port  (${AIRPLAY_PORTS[$port]})"
done
echo ""
echo "▶ gmediarender (UPnP/DLNA) 用ポート"
for port in "${!DLNA_PORTS[@]}"; do
    echo "  - $port  (${DLNA_PORTS[$port]})"
done
echo ""

read -rp "上記をローカルLAN ($SUBNET) からのみ開放します。続行しますか？ [Y/n] " ans
case "$ans" in
    [nN]*) echo "中止しました。"; read -rp "Enterで閉じます..." _; exit 0 ;;
esac

echo ""
echo "▶ ファイアウォールルールを追加中..."

for port in "${!AIRPLAY_PORTS[@]}" "${!DLNA_PORTS[@]}"; do
    sudo ufw allow from "$SUBNET" to any port "${port%%/*}" proto "${port##*/}" >/dev/null
    echo "  ✓ $port"
done

sudo ufw reload >/dev/null
echo ""
echo "✅ 完了しました。現在のルール:"
sudo ufw status numbered | grep -E "5353|7000|319|320|6000|1900|4915" || true

echo ""
read -rp "Enterで閉じます..." _
