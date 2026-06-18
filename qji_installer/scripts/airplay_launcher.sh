#!/bin/bash
# ============================================================
# Qji 奏在 — AirPlay レシーバー
#  経路: shairport-sync → ALSAループバック → ffmpeg(Musikverein) → DAC
# ============================================================

if [ -z "$TERM" ] || [ "$TERM" = "dumb" ]; then
    for _t in xfce4-terminal lxterminal mate-terminal xterm gnome-terminal konsole qterminal; do
        command -v "$_t" &>/dev/null && break
    done
    case "$_t" in
        xfce4-terminal) exec "$_t" --disable-server -T "📱 AirPlayレシーバー" -x bash "$0" "$@" ;;
        gnome-terminal) exec "$_t" --title "📱 AirPlayレシーバー" -- bash "$0" "$@" ;;
        *)              exec "$_t" -T "📱 AirPlayレシーバー" -e bash "$0" "$@" ;;
    esac
    exit $?
fi

QJI_DIR="$HOME/qji"
DEV_FILE="$QJI_DIR/.audio_devices"

if [ ! -f "$DEV_FILE" ]; then
    echo "⚠ オーディオデバイス設定が見つかりません。"
    echo "  先に「オーディオ基盤セットアップ」を実行してください。"
    read -rp "Enterで閉じます..." _
    exit 1
fi
# shellcheck disable=SC1090
source "$DEV_FILE"

cleanup() {
    echo ""
    echo "🛑 終了処理中..."
    [ -n "$SPS_PID" ] && kill "$SPS_PID" 2>/dev/null
    [ -n "$FF_PID" ]  && kill "$FF_PID" 2>/dev/null
    exit 0
}
trap cleanup INT TERM

echo "════════════════════════════════════════════════════"
echo "  📱 Qji × AirPlay レシーバー"
echo "════════════════════════════════════════════════════"
echo "  受信デバイス : $LOOPBACK_OUT"
echo "  出力デバイス : $OUTPUT_DEVICE"
echo "  音響処理     : Musikverein (Sonia Intelligence)"
echo "  停止         : Ctrl+C"
echo "────────────────────────────────────────────────────"
echo ""

if ! command -v shairport-sync &>/dev/null; then
    echo "⚠ shairport-sync がインストールされていません。"
    echo "  install.sh を再実行してください。"
    read -rp "Enterで閉じます..." _
    exit 1
fi

# システムのshairport-syncサービスが自動起動している場合は停止
# （出力デバイスを占有してQjiの再生が失敗するため）
if systemctl is-active --quiet shairport-sync 2>/dev/null; then
    echo "ℹ システムの shairport-sync サービスが起動中のため停止します..."
    sudo systemctl stop shairport-sync 2>/dev/null
    sleep 1
fi
pkill -x shairport-sync 2>/dev/null
sleep 1

DEVICE_NAME="Qji 奏在"

# 1) shairport-sync をALSAループバック入力側に向けて起動
SPS_LOG="/tmp/qji_shairport.log"
shairport-sync -a "$DEVICE_NAME" -o alsa -- -d "${LOOPBACK_IN}" > "$SPS_LOG" 2>&1 &
SPS_PID=$!
sleep 2

if ! kill -0 "$SPS_PID" 2>/dev/null; then
    echo "❌ shairport-sync の起動に失敗しました。ログ:"
    echo "──────────────────────────────────────────"
    tail -n 30 "$SPS_LOG"
    echo "──────────────────────────────────────────"
    read -rp "Enterで閉じます..." _
    exit 1
fi
echo "  ✓ shairport-sync 起動 (PID $SPS_PID) — デバイス名: $DEVICE_NAME"

# 2) ループバック出力 → ffmpeg(Musikverein系フィルター) → DAC
FF_LOG="/tmp/qji_airplay_ffmpeg.log"
(ffmpeg -loglevel error -f alsa -i "${LOOPBACK_OUT}" \
    -af "aresample=44100,equalizer=f=300:t=q:w=1:g=1.5,equalizer=f=5000:t=q:w=1:g=1,aecho=0.8:0.85:25:0.25,alimiter=limit=-1.5dB" \
    -f s32le -acodec pcm_s32le -ac 2 -ar 44100 - \
    | aplay -D "${OUTPUT_DEVICE}" -q -f S32_LE -c 2 -r 44100) > "$FF_LOG" 2>&1 &
FF_PID=$!
sleep 1

if ! kill -0 "$FF_PID" 2>/dev/null; then
    echo "❌ 再生パイプラインの起動に失敗しました。ログ:"
    echo "──────────────────────────────────────────"
    tail -n 30 "$FF_LOG"
    echo "──────────────────────────────────────────"
    kill "$SPS_PID" 2>/dev/null
    read -rp "Enterで閉じます..." _
    exit 1
fi
echo "  ✓ 再生パイプライン起動 (PID $FF_PID)"
echo ""
echo "  iPhone/Macの「AirPlay」から「$DEVICE_NAME」を選択してください。"
echo ""

set +e
wait
read -rp "Enterで閉じます..." _
