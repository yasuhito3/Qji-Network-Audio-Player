#!/bin/bash
# ============================================================
# Qji 奏在 — オーディオ基盤セットアップ
#  - snd-aloop (ALSAループバック) を永続化
#  - 接続中のUSB DAC等の出力デバイスを検出して保存
# ============================================================

if [ -z "$TERM" ] || [ "$TERM" = "dumb" ]; then
    for _t in xfce4-terminal lxterminal mate-terminal xterm gnome-terminal konsole qterminal; do
        command -v "$_t" &>/dev/null && break
    done
    case "$_t" in
        xfce4-terminal) exec "$_t" --disable-server -T "🔧 オーディオ基盤セットアップ" -x bash "$0" "$@" ;;
        gnome-terminal) exec "$_t" --title "🔧 オーディオ基盤セットアップ" -- bash "$0" "$@" ;;
        *)              exec "$_t" -T "🔧 オーディオ基盤セットアップ" -e bash "$0" "$@" ;;
    esac
    exit $?
fi

trap 'ec=$?; echo ""; echo "エラー（終了コード: $ec）。Enterで閉じます..."; read _; exit 1' ERR

echo "╔══════════════════════════════════════════╗"
echo "║   Qji 奏在 — オーディオ基盤セットアップ    ║"
echo "╚══════════════════════════════════════════╝"
echo ""

QJI_DIR="$HOME/qji"
mkdir -p "$QJI_DIR"

# ------------------------------------------------------------
# 1. snd-aloop の永続化
#    （gmediarender / AirPlay の受け口として使用）
# ------------------------------------------------------------
step1() {
echo "▶ ALSAループバック (snd-aloop) を確認中..."

if ! lsmod | grep -q snd_aloop; then
    sudo modprobe snd-aloop pcm_substreams=4
fi

if [ ! -f /etc/modules-load.d/qji-aloop.conf ]; then
    echo "snd-aloop" | sudo tee /etc/modules-load.d/qji-aloop.conf >/dev/null
    echo "options snd-aloop pcm_substreams=4" | sudo tee /etc/modprobe.d/qji-aloop.conf >/dev/null
    echo "  ✓ 起動時に snd-aloop を自動ロードするよう設定しました"
else
    echo "  ✓ 既に設定済みです"
fi
}
step1

echo ""

# ------------------------------------------------------------
# 2. 出力デバイス（USB DAC）の検出
# ------------------------------------------------------------
echo "▶ 接続中の再生デバイス一覧:"
echo ""
LC_ALL=C aplay -l | grep -E "^card" | sed 's/^/  /'
echo ""

LOOPBACK_CARD=$(LC_ALL=C aplay -l | grep -i "Loopback" | head -1 | sed -E 's/^card ([0-9]+).*/\1/')
DAC_CARD=$(LC_ALL=C aplay -l | grep -vi "Loopback\|HDMI\|bcm2835" | grep -E "^card" | head -1 | sed -E 's/^card ([0-9]+).*/\1/')

if [ -z "$DAC_CARD" ]; then
    DAC_CARD=0
fi
if [ -z "$LOOPBACK_CARD" ]; then
    LOOPBACK_CARD=1
fi

echo "推定された設定:"
echo "  出力(DAC)用デバイス     : hw:${DAC_CARD},0"
echo "  ループバック(受信)デバイス: hw:${LOOPBACK_CARD},0 / hw:${LOOPBACK_CARD},1"
echo ""
read -rp "出力(DAC)デバイスのカード番号 [${DAC_CARD}]: " input_dac
DAC_CARD="${input_dac:-$DAC_CARD}"
read -rp "ループバックのカード番号 [${LOOPBACK_CARD}]: " input_lb
LOOPBACK_CARD="${input_lb:-$LOOPBACK_CARD}"

cat > "$QJI_DIR/.audio_devices" << EOF
# Qji 奏在 — オーディオデバイス設定（setup_audio_loopback.sh が生成）
OUTPUT_DEVICE=hw:${DAC_CARD},0
LOOPBACK_IN=hw:${LOOPBACK_CARD},1,0
LOOPBACK_OUT=hw:${LOOPBACK_CARD},0,0
EOF

echo ""
echo "✅ ~/qji/.audio_devices を保存しました:"
cat "$QJI_DIR/.audio_devices" | sed 's/^/   /'
echo ""
echo "  Qji本体の出力先(hw:X,0)を変更したい場合は、"
echo "  ~/qji/qji.py 内の output_device / --device を上記に合わせてください。"
echo ""
read -rp "Enterで閉じます..." _
