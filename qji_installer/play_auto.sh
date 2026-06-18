#!/bin/bash

INPUT="$1"

if [ -z "$INPUT" ]; then
    echo "使い方: ./play_auto.sh 音源.wav"
    exit 1
fi

# ファイル存在確認
if [ ! -f "$INPUT" ]; then
    echo "エラー: ファイルが見つかりません: $INPUT"
    exit 1
fi

# ======================
# ① 簡易ジャンル判定
# ======================

FILENAME=$(basename "$INPUT" | tr '[:upper:]' '[:lower:]')
GENRE="unknown"

case "$FILENAME" in
    *piano*)
        GENRE="piano" ;;
    *orch*|*symph*)
        GENRE="orchestra" ;;
    *vocal*|*song*)
        GENRE="vocal" ;;
    *)
        # ffmpegでRMSレベルを取得（失敗時はpopにフォールバック）
        BASS=$(ffmpeg -i "$INPUT" \
            -af "astats=metadata=1:reset=1" \
            -f null - 2>&1 \
            | grep "RMS level dB" | head -n 1 | awk '{print $NF}')

        if [ -z "$BASS" ]; then
            GENRE="pop"
        elif awk "BEGIN { exit !($BASS < -20) }"; then
            GENRE="piano"
        else
            GENRE="pop"
        fi
        ;;
esac

echo "推定ジャンル: $GENRE"

# ======================
# ② プリセット定義
# ======================

case "$GENRE" in
    piano)
        FILTER="equalizer=f=8000:t=q:w=1:g=2,equalizer=f=120:t=q:w=0.8:g=-2,aecho=0.8:0.9:15:0.15"
        ;;
    orchestra)
        FILTER="equalizer=f=300:t=q:w=1:g=2,equalizer=f=5000:t=q:w=1:g=1,stereotools=mlev=1.2,aecho=0.85:0.9:25:0.25"
        ;;
    vocal)
        FILTER="equalizer=f=3000:t=q:w=1:g=2,equalizer=f=120:t=q:w=1:g=-1,acompressor=threshold=-18dB:ratio=2"
        ;;
    pop)
        FILTER="equalizer=f=80:t=q:w=1:g=3,equalizer=f=4000:t=q:w=1:g=2,acompressor=threshold=-20dB:ratio=2.5"
        ;;
    *)
        FILTER="anull"
        ;;
esac

# ======================
# ③ 再生（32bit / Amanero対応）
# ======================

echo "適用フィルタ:"
echo "$FILTER"

# -f s32le でraw PCMを出力し、aplayと形式を厳密に一致させる
# -D hw:2,0 でデバイスを明示（← これが修正の核心）
ffmpeg -loglevel error -i "$INPUT" \
    -af "$FILTER" \
    -f s32le -acodec pcm_s32le -ac 2 -ar 44100 - \
    | aplay -D hw:2,0 -q -f S32_LE -c 2 -r 44100

EXIT_CODE=${PIPESTATUS[0]}
if [ "$EXIT_CODE" -ne 0 ]; then
    echo "エラー: ffmpeg が終了コード $EXIT_CODE を返しました"
fi
