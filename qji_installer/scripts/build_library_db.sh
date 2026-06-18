#!/bin/bash
# ============================================================
# Qji 奏在 — 音源ライブラリーDB構築 (music_mood_db.json)
# ============================================================

if [ -z "$TERM" ] || [ "$TERM" = "dumb" ]; then
    for _t in xfce4-terminal lxterminal mate-terminal xterm gnome-terminal konsole qterminal; do
        command -v "$_t" &>/dev/null && break
    done
    case "$_t" in
        xfce4-terminal) exec "$_t" --disable-server -T "🗄 音源ライブラリー構築" -x bash "$0" "$@" ;;
        gnome-terminal) exec "$_t" --title "🗄 音源ライブラリー構築" -- bash "$0" "$@" ;;
        *)              exec "$_t" -T "🗄 音源ライブラリー構築" -e bash "$0" "$@" ;;
    esac
    exit $?
fi

QJI_DIR="$HOME/qji"
MARKER="$HOME/.qji_library_scanned"

# ロケールに応じた「ミュージック」フォルダを取得
MUSIC_XDG="$(xdg-user-dir MUSIC 2>/dev/null)"
[ -z "$MUSIC_XDG" ] && MUSIC_XDG="$HOME/Music"

# $USER が未設定の場合に備えてフォールバック
QJI_USER="${USER:-$(whoami)}"

# スキャン対象ディレクトリ（存在するものだけ）
SCAN_DIRS=()
[ -d "$MUSIC_XDG" ] && SCAN_DIRS+=("$MUSIC_XDG")
[ -d "$HOME/Music" ] && [ "$HOME/Music" != "$MUSIC_XDG" ] && SCAN_DIRS+=("$HOME/Music")
[ -d "/media/$QJI_USER" ] && SCAN_DIRS+=("/media/$QJI_USER")
[ -d "/run/media/$QJI_USER" ] && SCAN_DIRS+=("/run/media/$QJI_USER")
[ -d "/media" ] && SCAN_DIRS+=("/media")
[ -d "/mnt" ] && SCAN_DIRS+=("/mnt")
[ -d "/run/user/$(id -u)/gvfs" ] && SCAN_DIRS+=("/run/user/$(id -u)/gvfs")

# 重複・親子関係のあるパスを除去（/media と /media/$USER 等）
UNIQ_DIRS=()
for d in "${SCAN_DIRS[@]}"; do
    skip=0
    for u in "${UNIQ_DIRS[@]}"; do
        case "$d/" in "$u"/*) skip=1; break;; esac
    done
    [ $skip -eq 0 ] && UNIQ_DIRS+=("$d")
done
SCAN_DIRS=("${UNIQ_DIRS[@]}")

# 引数指定があればそれを優先
if [ -n "$1" ]; then
    SCAN_DIRS=("$1")
fi

clear
LOG_FILE="$QJI_DIR/library_build_debug.log"
exec > >(tee "$LOG_FILE") 2>&1

echo "╔══════════════════════════════════════════════════╗"
echo "║   🗄  Qji 奏在 — 音源ライブラリーDB構築           ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "  対象フォルダ:"
for d in "${SCAN_DIRS[@]}"; do
    echo "    - $d"
done
echo "  保存先      : ~/music_mood_db.json"
echo "  ログ        : $LOG_FILE  ← この内容はコピー可能です"
echo ""

# ── 事前診断: 各フォルダの対応形式ファイル数 ──────────────
echo "▶ 事前診断（対応形式ファイル数）:"
EXTS="flac mp3 wav m4a aac ogg wma aiff aif dsf dff ape opus"
FIND_EXPR=()
for e in $EXTS; do
    FIND_EXPR+=(-iname "*.${e}" -o)
done
unset 'FIND_EXPR[${#FIND_EXPR[@]}-1]'  # 末尾の -o を除去

TOTAL=0
for d in "${SCAN_DIRS[@]}"; do
    cnt=$(find "$d" -type f \( "${FIND_EXPR[@]}" \) 2>/dev/null | wc -l)
    echo "    $d : ${cnt} ファイル"
    TOTAL=$((TOTAL + cnt))
done
echo "    合計: ${TOTAL} ファイル"
echo ""

if [ "$TOTAL" -eq 0 ]; then
    echo "⚠ 対応形式の音源ファイルが1つも見つかりませんでした。"
    echo ""
    echo "  参考: /media, /run/user/$(id -u)/gvfs の内容"
    echo "──────────────────────────────────────────────────"
    for p in "/media" "/media/$QJI_USER" "/run/media/$QJI_USER" "/run/user/$(id -u)/gvfs"; do
        if [ -d "$p" ]; then
            echo "  $p :"
            ls -la "$p" 2>/dev/null | sed 's/^/    /'
        fi
    done
    echo ""
    echo "  現在のマウント状況"
    echo "──────────────────────────────────────────────────"
    mount | grep -E "/media|/mnt|gvfs|AudioFiles" | sed 's/^/    /'
    echo "──────────────────────────────────────────────────"
    echo ""
    read -rp "Enterキーで閉じます..." _
    exit 1
fi

echo "  曲数が多い場合、初回は時間がかかります"
echo "  （API利用のため1曲あたり待機が入ります）。"
echo "  途中で中断したい場合は Ctrl+C を押してください。"
echo "  （中断してもそこまでの結果は保存されます）"
echo ""
echo "──────────────────────────────────────────────────"
echo ""

python3 "$QJI_DIR/scripts/music_library_analyzer.py" --dirs "${SCAN_DIRS[@]}" --no-wait
EXIT_CODE=$?

echo ""
echo "──────────────────────────────────────────────────"
if [ $EXIT_CODE -eq 0 ]; then
    touch "$MARKER"
    echo "✅ ライブラリーDBの構築が完了しました。"
    echo "   Qji 奏在 を起動してお楽しみください。"
else
    echo "⚠ 終了コード: $EXIT_CODE"
    echo "   エラーが発生したか、中断されました。"
    echo "   再度このアイコンを実行すると、続きから処理されます。"
fi
echo ""
read -rp "Enterキーで閉じます..." _
