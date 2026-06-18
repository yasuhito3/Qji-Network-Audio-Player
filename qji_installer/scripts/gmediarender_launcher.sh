#!/bin/bash
# ============================================================
# Qji 奏在 — gmediarender (UPnP/DLNA) レシーバー
#  経路: gmediarender → ALSAループバック → ffmpeg(Musikverein) → DAC
# ============================================================

if [ -z "$TERM" ] || [ "$TERM" = "dumb" ]; then
    for _t in xfce4-terminal lxterminal mate-terminal xterm gnome-terminal konsole qterminal; do
        command -v "$_t" &>/dev/null && break
    done
    case "$_t" in
        xfce4-terminal) exec "$_t" --disable-server -T "📡 gmediarender レシーバー" -x bash "$0" "$@" ;;
        gnome-terminal) exec "$_t" --title "📡 gmediarender レシーバー" -- bash "$0" "$@" ;;
        *)              exec "$_t" -T "📡 gmediarender レシーバー" -e bash "$0" "$@" ;;
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
    [ -n "$GMR_PID" ] && kill "$GMR_PID" 2>/dev/null
    [ -n "$FF_PID" ]  && kill "$FF_PID" 2>/dev/null
    exit 0
}
trap cleanup INT TERM

echo "════════════════════════════════════════════════════"
echo "  📡 Qji × gmediarender (UPnP/DLNA レシーバー)"
echo "════════════════════════════════════════════════════"
echo "  受信デバイス : $LOOPBACK_OUT"
echo "  出力デバイス : $OUTPUT_DEVICE"
echo "  音響処理     : Musikverein (Sonia Intelligence)"
echo "  停止         : Ctrl+C"
echo "────────────────────────────────────────────────────"
echo ""

if ! command -v gmediarender &>/dev/null; then
    echo "⚠ gmediarender がインストールされていません。"
    echo "  install.sh を再実行してください。"
    read -rp "Enterで閉じます..." _
    exit 1
fi

# システムのgmediarenderサービスが自動起動している場合は停止
if systemctl is-active --quiet gmediarender 2>/dev/null; then
    echo "ℹ システムの gmediarender サービスが起動中のため停止します..."
    sudo systemctl stop gmediarender 2>/dev/null
    sleep 1
fi
pkill -x gmediarender 2>/dev/null
sleep 1

trap 'echo ""; echo "----------------------------------------"; echo "エラーが発生しました。上のログを確認してください。"; read -rp "Enterで閉じます..." _; exit 1' ERR
set -e

# --- ハイレゾ自動検出: ループバック出力の実サンプルレートをffmpegに渡す ---
# ffmpeg側で自動検出させるため -af aresample を使用

# 1) gmediarender をALSAループバック入力側に向けて起動
GMR_LOG="/tmp/qji_gmediarender.log"
LANG=C.UTF-8 LC_ALL=C.UTF-8 gmediarender -f "Qji Player" \
    --gstout-audiosink=alsasink \
    --gstout-audiodevice="${LOOPBACK_IN}" \
    > "$GMR_LOG" 2>&1 &
GMR_PID=$!
sleep 2

if ! kill -0 "$GMR_PID" 2>/dev/null; then
    echo "❌ gmediarender の起動に失敗しました。ログ:"
    echo "──────────────────────────────────────────"
    tail -n 30 "$GMR_LOG"
    echo "──────────────────────────────────────────"
    echo "📖 利用可能なオプション (--help):"
    echo "──────────────────────────────────────────"
    gmediarender --help 2>&1 | grep -iE "gstout|audio|device|sink" | head -20
    echo "──────────────────────────────────────────"
    read -rp "Enterで閉じます..." _
    exit 1
fi
echo "  ✓ gmediarender 起動 (PID $GMR_PID)"

# 2) ループバック出力 → ffmpeg(Musikverein系フィルター) → DAC
FF_LOG="/tmp/qji_gmr_ffmpeg.log"
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
    kill "$GMR_PID" 2>/dev/null
    read -rp "Enterで閉じます..." _
    exit 1
fi
echo "  ✓ 再生パイプライン起動 (PID $FF_PID)"
echo ""
echo "  他の機器（スマホ等）からこの曲を「Qji Player」へ"
echo "  キャストしてください。"
echo ""

set +e
wait
read -rp "Enterで閉じます..." _
