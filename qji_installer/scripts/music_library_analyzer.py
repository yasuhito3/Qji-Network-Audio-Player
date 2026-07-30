import os
import json
import sys
from mutagen import File
import librosa
import numpy as np
import warnings
import time
import gc
import logging
from pathlib import Path
import multiprocessing as mp
from typing import Dict, List, Optional, Tuple
import traceback
import re
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from functools import lru_cache
import hashlib
import signal

warnings.filterwarnings('ignore')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('music_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

MUSIC_DIRS = [
    '/var/lib/mpd/music',
    os.path.expanduser('~/Music'),
    os.path.expanduser('~/AudioFiles'),
    os.path.expanduser('~/SoundFiles'),
    '/media',
    '/mnt',  # SoundgenicなどSMBマウント全般もこの配下にあれば自動的に対象になる
]

# ネットワークマウント（SMB/CIFS等）でos.walk中に接続が瞬断した場合、
# OSError/TimeoutErrorが発生してもスキャン全体を止めずに次のディレクトリへ進む
NETWORK_WALK_ERROR_HANDLER = lambda err: logger.warning(f"⚠️ ディレクトリ走査エラー（スキップして続行）: {err}")
SUPPORTED_EXTENSIONS = ('.wav', '.flac', '.wma', '.aiff', '.mp3', '.m4a', '.aac', '.ogg')

# MUSIC_ANALYZER_DB_FILE環境変数、または--db-file引数で上書き可能。
# これにより、テスト実行が誤って本番の音源データベースに触れることを防げる。
DATABASE_FILE = os.environ.get(
    'MUSIC_ANALYZER_DB_FILE',
    os.path.expanduser('~/music_mood_db.json')
)
BACKUP_INTERVAL = 50
MAX_RETRIES = 3
ANALYSIS_TIMEOUT = 60

# --yes フラグ、または非対話環境で自動承認するかどうか（デフォルトは常に確認する）
AUTO_CONFIRM = False


def confirm_action(message: str, default_no: bool = True) -> bool:
    """
    破壊的な操作（削除・強制再スキャンによる上書き等）の前に必ず確認する。

    - --yes フラグが指定されていれば自動承認（自動化・シェルスクリプトからの
      呼び出し用。ただしユーザーが明示的にリスクを了承した場合のみ使うこと）
    - 標準入力がttyでない（cron等の完全非対話環境）場合は、安全側に倒して
      自動的に「いいえ」とする（黙って削除・上書きすることは絶対にしない）
    - それ以外は必ずy/n入力を求める
    """
    if AUTO_CONFIRM:
        logger.info(f"✅ (--yes指定により自動承認): {message}")
        return True

    if not sys.stdin.isatty():
        logger.warning(
            f"⚠️ 非対話環境のため、確認が必要な操作を自動的に中止しました: {message}\n"
            f"   自動実行時にこの操作を許可する場合は --yes を明示的に指定してください。"
        )
        return False

    answer = input(f"\n⚠️  {message}\n   続行しますか？ [y/N]: ").strip().lower()
    return answer in ('y', 'yes')

MUSICBRAINZ_BASE_URL = "https://musicbrainz.org/ws/2"
LASTFM_BASE_URL = "http://ws.audioscrobbler.com/2.0/"
LASTFM_API_KEY = "ed2d56a3422332f5d2aa42cd23531127"
API_CACHE_FILE = os.path.expanduser('~/music_api_cache.json')
API_REQUEST_DELAY = 1.0

# 拡張ムードマッピング（Last.fmタグから直接ムードを抽出）
LASTFM_TAG_TO_MOOD = {
    # ポジティブ・明るい系
    'happy': 'happy',
    'cheerful': 'happy',
    'joyful': 'happy',
    'uplifting': 'uplifting',
    'upbeat': 'upbeat',
    'fun': 'playful',
    'playful': 'playful',
    'party': 'energetic',
    
    # エネルギッシュ系
    'energetic': 'energetic',
    'powerful': 'powerful',
    'intense': 'intense',
    'aggressive': 'aggressive',
    'epic': 'epic',
    'triumphant': 'triumphant',
    'driving': 'energizing',
    
    # 穏やか・リラックス系
    'calm': 'calm',
    'peaceful': 'peaceful',
    'relaxing': 'relaxing',
    'chill': 'chill',
    'chillout': 'chill',
    'tranquil': 'serene',
    'serene': 'serene',
    'soothing': 'soothing',
    'ambient': 'ambient',
    'atmospheric': 'atmospheric',
    
    # メロウ・優しい系
    'mellow': 'mellow',
    'smooth': 'smooth',
    'soft': 'tender',
    'gentle': 'tender',
    'tender': 'tender',
    'sweet': 'sweet',
    
    # 感情的・ドラマチック系
    'emotional': 'emotional',
    'dramatic': 'dramatic',
    'passionate': 'passionate',
    'romantic': 'romantic',
    'intimate': 'intimate',
    'sensual': 'sensual',
    
    # ダーク・メランコリック系
    'dark': 'dark',
    'melancholy': 'melancholy',
    'melancholic': 'melancholy',
    'sad': 'melancholy',
    'depressing': 'somber',
    'somber': 'somber',
    'gloomy': 'dark',
    'brooding': 'dark',
    
    # 神秘的・幻想的系
    'mysterious': 'mysterious',
    'mystical': 'mysterious',
    'ethereal': 'ethereal',
    'dreamy': 'dreamy',
    'psychedelic': 'psychedelic',
    'hypnotic': 'hypnotic',
    
    # グルーヴ・ファンク系
    'groovy': 'groovy',
    'funky': 'funky',
    'rhythmic': 'groovy',
    'danceable': 'danceable',
    
    # その他特徴的なムード
    'nostalgic': 'nostalgic',
    'longing': 'nostalgic',
    'beauty': 'beautiful',
    'beautiful': 'beautiful',
    'inspiring': 'inspiring',
    'motivational': 'inspiring',
}

# ジャンル別デフォルトムード（APIが失敗した時のフォールバック）
GENRE_DEFAULT_MOODS = {
    'classical': ['serene', 'dramatic', 'elegant'],
    'jazz': ['groovy', 'smooth', 'sophisticated'],
    'blues': ['melancholy', 'soulful', 'groovy'],
    'rock': ['energetic', 'powerful', 'rebellious'],
    'metal': ['aggressive', 'intense', 'powerful'],
    'electronic': ['atmospheric', 'energizing', 'hypnotic'],
    'ambient': ['atmospheric', 'ethereal', 'meditative'],
    'folk': ['nostalgic', 'peaceful', 'intimate'],
    'pop': ['upbeat', 'catchy', 'cheerful'],
    'hip-hop': ['groovy', 'energetic', 'confident'],
    'r&b': ['smooth', 'sensual', 'soulful'],
    'soul': ['emotional', 'passionate', 'soulful'],
    'funk': ['funky', 'groovy', 'danceable'],
    'disco': ['danceable', 'upbeat', 'groovy'],
    'house': ['energizing', 'hypnotic', 'uplifting'],
    'techno': ['hypnotic', 'driving', 'intense'],
    'trance': ['uplifting', 'ethereal', 'euphoric'],
    'reggae': ['chill', 'peaceful', 'groovy'],
    'country': ['nostalgic', 'storytelling', 'heartfelt'],
    'soundtrack': ['cinematic', 'epic', 'dramatic'],
}

COMPOSER_NORMALIZATION = {
    'antonin dvorak': 'A. Dvorak',
    'bela bartok': 'B. Bartok',
    'dvorak': 'A. Dvorak',
    'frederic chopin': 'F. Chopin',
    'bach': 'J.S. Bach',
    'bartok': 'B. Bartók',
    'beethoven': 'L.v. Beethoven',
    'brahms': 'J. Brahms',
    'chopin': 'F. Chopin',
    'claude debussy': 'C. Debussy',
    'debussy': 'C. Debussy',
    'dmitri shostakovich': 'D. Shostakovich',
    'felix mendelssohn': 'F. Mendelssohn',
    'franz joseph haydn': 'F.J. Haydn',
    'franz liszt': 'F. Liszt',
    'franz schubert': 'F. Schubert',
    'george frideric handel': 'G.F. Handel',
    'giuseppe verdi': 'G. Verdi',
    'gustav mahler': 'G. Mahler',
    'handel': 'G.F. Handel',
    'haydn': 'F.J. Haydn',
    'igor stravinsky': 'I. Stravinsky',
    'j.s. bach': 'J.S. Bach',
    'j. brahms': 'J. Brahms',
    'jean sibelius': 'J. Sibelius',
    'johann sebastian bach': 'J.S. Bach',
    'johannes brahms': 'J. Brahms',
    'joseph haydn': 'F.J. Haydn',
    'js bach': 'J.S. Bach',
    'liszt': 'F. Liszt',
    'ludwig van beethoven': 'L.v. Beethoven',
    'l.v. beethoven': 'L.v. Beethoven',
    'mahler': 'G. Mahler',
    'maurice ravel': 'M. Ravel',
    'mendelssohn': 'F. Mendelssohn',
    'mozart': 'W.A. Mozart',
    'prokofiev': 'S. Prokofiev',
    'pyotr ilyich tchaikovsky': 'P.I. Tchaikovsky',
    'rachmaninoff': 'S. Rachmaninoff',
    'ravel': 'M. Ravel',
    'richard strauss': 'R. Strauss',
    'richard wagner': 'R. Wagner',
    'robert schumann': 'R. Schumann',
    'schoenberg': 'A. Schoenberg',
    'schubert': 'F. Schubert',
    'schumann': 'R. Schumann',
    'sergei prokofiev': 'S. Prokofiev',
    'sergei rachmaninoff': 'S. Rachmaninoff',
    'shostakovich': 'D. Shostakovich',
    'sibelius': 'J. Sibelius',
    'strauss': 'R. Strauss',
    'stravinsky': 'I. Stravinsky',
    'tchaikovsky': 'P.I. Tchaikovsky',
    'verdi': 'G. Verdi',
    'vivaldi': 'A. Vivaldi',
    'w.a. mozart': 'W.A. Mozart',
    'wagner': 'R. Wagner',
    'wolfgang amadeus mozart': 'W.A. Mozart',
}

GENRE_NORMALIZATION = {
    'ambient': 'Ambient',
    'ambience': 'Ambient',
    'blue': 'Blues',
    'blues': 'Blues',
    'classic': 'Classical',
    'classic metal': 'Metal',
    'classic rock': 'Rock',
    'classical': 'Classical',
    'classica': 'Classical',
    'classique': 'Classical',
    'country': 'Country',
    'country music': 'Country',
    'dance': 'Dance',
    'dance music': 'Dance',
    'electro': 'Electronic',
    'electronic': 'Electronic',
    'electronica': 'Electronic',
    'folk': 'Folk',
    'folk music': 'Folk',
    'heavy metal': 'Heavy Metal',
    'hip hop': 'Hip-Hop',
    'hip-hop': 'Hip-Hop',
    'hiphop': 'Hip-Hop',
    'j-pop': 'J-Pop',
    'jazz': 'Jazz',
    'jazz fusion': 'Jazz Fusion',
    'jazzy': 'Jazz',
    'k-pop': 'K-Pop',
    'klassik': 'Classical',
    'metal': 'Metal',
    'ost': 'Soundtrack',
    'pop': 'Pop',
    'pop music': 'Pop',
    'pop/rock': 'Pop Rock',
    'r&b': 'R&B',
    'rap': 'Hip-Hop',
    'rhythm and blues': 'R&B',
    'rnb': 'R&B',
    'rock': 'Rock',
    'rock & roll': 'Rock',
    'rock and roll': 'Rock',
    'rock/pop': 'Rock',
    'soundtrack': 'Soundtrack',
    'world': 'World Music',
    'world music': 'World Music',
}

PERFORMER_NORMALIZATION = {
    'arthur rubinstein': 'Arthur Rubinstein',
    'berlin philharmonic': 'Berlin Philharmonic Orchestra',
    'berliner philharmoniker': 'Berlin Philharmonic Orchestra',
    'daniel barenboim': 'Daniel Barenboim',
    'dietrich fischer-dieskau': 'Dietrich Fischer-Dieskau',
    'evgeny kissin': 'Evgeny Kissin',
    'glenn gould': 'Glenn Gould',
    'herbert von karajan': 'Herbert von Karajan',
    'hilary hahn': 'Hilary Hahn',
    'itzhak perlman': 'Itzhak Perlman',
    'karajan': 'Herbert von Karajan',
    'lang lang': 'Lang Lang',
    'leonard bernstein': 'Leonard Bernstein',
    'london symphony orchestra': 'London Symphony Orchestra',
    'lso': 'London Symphony Orchestra',
    'maria callas': 'Maria Callas',
    'martha argerich': 'Martha Argerich',
    'maurizio pollini': 'Maurizio Pollini',
    'new york philharmonic': 'New York Philharmonic',
    'paavo jarvi': 'Paavo Jarvi',
    'placido domingo': 'Placido Domingo',
    'riccardo muti': 'Riccardo Muti',
    'vienna philharmonic': 'Vienna Philharmonic Orchestra',
    'wiener philharmoniker': 'Vienna Philharmonic Orchestra',
    'yo-yo ma': 'Yo-Yo Ma',
    'yuja wang': 'Yuja Wang',
}

def normalize_composer_name(composer: str) -> str:
    if not composer or composer in ['Unknown', 'None', '']:
        return 'Unknown'
    composer_lower = composer.strip().lower()
    if composer_lower in COMPOSER_NORMALIZATION:
        normalized = COMPOSER_NORMALIZATION[composer_lower]
        logger.debug(f"作曲家名正規化: '{composer}' → '{normalized}'")
        return normalized
    return composer.strip().title()

def normalize_genre_name(genre: str) -> str:
    if not genre or genre in ['Unknown', 'None', '']:
        return 'Unknown'
    if ';' in genre or '/' in genre or ',' in genre:
        genre = re.split('[;/,]', genre)[0].strip()
    genre_lower = genre.strip().lower()
    if genre_lower in GENRE_NORMALIZATION:
        normalized = GENRE_NORMALIZATION[genre_lower]
        logger.debug(f"ジャンル名正規化: '{genre}' → '{normalized}'")
        return normalized
    for key, value in GENRE_NORMALIZATION.items():
        if key in genre_lower or genre_lower in key:
            logger.debug(f"ジャンル名正規化(部分一致): '{genre}' → '{value}'")
            return value
    return genre.strip().title()

def normalize_performer_name(performer: str) -> str:
    if not performer or performer in ['Unknown', 'None', '']:
        return 'Unknown'
    performer_lower = performer.strip().lower()
    if performer_lower in PERFORMER_NORMALIZATION:
        normalized = PERFORMER_NORMALIZATION[performer_lower]
        logger.debug(f"演奏者名正規化: '{performer}' → '{normalized}'")
        return normalized
    return performer.strip().title()

class AudioAnalysisError(Exception):
    pass

class APICache:
    def __init__(self, cache_file: str = API_CACHE_FILE):
        self.cache_file = cache_file
        self.cache = self._load_cache()
        self.last_save = time.time()
        self.save_interval = 300  # 5分に1回に変更
        self.pending_changes = 0
        self.max_pending = 100  # 100件変更ごとに保存
    
    def _load_cache(self) -> Dict:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data
            except Exception as e:
                logger.warning(f"キャッシュ読み込みエラー: {e}")
        return {'musicbrainz': {}, 'lastfm': {}}
    
    def save_cache(self, force: bool = False):
        """改良版：ファイルハンドル確実クローズ"""
        current_time = time.time()
        should_save = (
            force or 
            (current_time - self.last_save) > self.save_interval or
            self.pending_changes >= self.max_pending
        )
        
        if should_save:
            temp_file = f"{self.cache_file}.tmp"
            try:
                # 確実にファイルを閉じる
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(self.cache, f, ensure_ascii=False, indent=2)
                
                # 原子的に置き換え
                if os.path.exists(self.cache_file):
                    os.replace(temp_file, self.cache_file)
                else:
                    os.rename(temp_file, self.cache_file)
                
                self.last_save = current_time
                self.pending_changes = 0
                logger.debug(f"APIキャッシュ保存完了: {len(self.cache.get('lastfm', {}))}件")
                
            except Exception as e:
                logger.error(f"キャッシュ保存エラー: {e}")
                # 一時ファイルのクリーンアップ
                if os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
    
    def get_cache_key(self, artist: str, title: str, source: str) -> str:
        key_str = f"{artist}|{title}".lower().strip()
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()
    
    def get(self, artist: str, title: str, source: str) -> Optional[Dict]:
        key = self.get_cache_key(artist, title, source)
        return self.cache.get(source, {}).get(key)
    
    def set(self, artist: str, title: str, source: str, data: Dict):
        """改良版：即座に保存せず、バッチ処理"""
        key = self.get_cache_key(artist, title, source)
        if source not in self.cache:
            self.cache[source] = {}
        self.cache[source][key] = {'data': data, 'timestamp': time.time()}
        
        self.pending_changes += 1
        # 定期的に自動保存
        self.save_cache(force=False)

class MusicBrainzAPI:
    def __init__(self, cache: APICache):
        self.cache = cache
        self.session = self._create_session()
        self.last_request_time = 0
        self.user_agent = "MusicAnalyzer/2.0"
    
    def _create_session(self):
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session
    
    def _rate_limit(self):
        elapsed = time.time() - self.last_request_time
        if elapsed < API_REQUEST_DELAY:
            time.sleep(API_REQUEST_DELAY - elapsed)
        self.last_request_time = time.time()
    
    def search_recording(self, artist: str, title: str) -> Optional[Dict]:
        if artist == 'Unknown' or title == 'Unknown':
            return None
        cached = self.cache.get(artist, title, 'musicbrainz')
        if cached:
            logger.debug(f"MusicBrainzキャッシュヒット: {artist} - {title}")
            return cached.get('data')
        try:
            self._rate_limit()
            params = {
                'query': f'artist:"{artist}" AND recording:"{title}"',
                'fmt': 'json', 'limit': 1, 'inc': 'artist-credits+tags+work-rels'
            }
            headers = {'User-Agent': self.user_agent}
            response = self.session.get(f"{MUSICBRAINZ_BASE_URL}/recording", params=params, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                recordings = data.get('recordings', [])
                if recordings:
                    recording = recordings[0]
                    composer = None
                    performer = None
                    conductor = None
                    for relation in recording.get('relations', []):
                        if relation.get('type') == 'composer':
                            composer = relation.get('artist', {}).get('name')
                        elif relation.get('type') == 'conductor':
                            conductor = relation.get('artist', {}).get('name')
                        elif relation.get('type') == 'performer':
                            performer = relation.get('artist', {}).get('name')
                    artist_credits = recording.get('artist-credit', [])
                    if artist_credits and not performer:
                        performer = artist_credits[0].get('name')
                    result = {
                        'mbid': recording.get('id'), 'title': recording.get('title'),
                        'composer': composer, 'conductor': conductor, 'performer': performer,
                        'tags': [tag['name'] for tag in recording.get('tags', [])],
                        'genres': [tag['name'] for tag in recording.get('tags', []) if tag.get('count', 0) > 0]
                    }
                    self.cache.set(artist, title, 'musicbrainz', result)
                    return result
            elif response.status_code == 429:
                time.sleep(5)
        except Exception as e:
            logger.debug(f"MusicBrainz検索エラー: {e}")
        return None

class LastFmAPI:
    def __init__(self, api_key: str, cache: APICache):
        self.api_key = api_key
        self.cache = cache
        self.session = self._create_session()
        self.enabled = bool(api_key)
    
    def _create_session(self):
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session
    
    def get_track_info(self, artist: str, title: str) -> Optional[Dict]:
        if not self.enabled or artist == 'Unknown' or title == 'Unknown':
            return None
        cached = self.cache.get(artist, title, 'lastfm')
        if cached:
            logger.debug(f"Last.fmキャッシュヒット: {artist} - {title}")
            return cached.get('data')
        try:
            params = {'method': 'track.getInfo', 'api_key': self.api_key, 'artist': artist, 'track': title, 'format': 'json'}
            response = self.session.get(LASTFM_BASE_URL, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'track' in data:
                    track = data['track']
                    result = {
                        'name': track.get('name'), 'artist': track.get('artist', {}).get('name'),
                        'album': track.get('album', {}).get('title'),
                        'tags': [tag['name'] for tag in track.get('toptags', {}).get('tag', [])]
                    }
                    self.cache.set(artist, title, 'lastfm', result)
                    logger.info(f"✓ Last.fm: {artist} - {title} → タグ: {result['tags'][:5]}")
                    return result
        except Exception as e:
            logger.debug(f"Last.fm検索エラー: {e}")
        return None
    
    def infer_mood_from_tags(self, tags: List[str]) -> Optional[str]:
        """Last.fmタグから直接ムードを推測（優先度順）"""
        if not tags:
            return None
        
        tags_lower = [tag.lower() for tag in tags]
        
        # タグの優先度順にチェック（より具体的なムードを優先）
        mood_scores = {}
        
        for tag in tags_lower:
            # 完全一致
            if tag in LASTFM_TAG_TO_MOOD:
                mood = LASTFM_TAG_TO_MOOD[tag]
                mood_scores[mood] = mood_scores.get(mood, 0) + 10
            
            # 部分一致（例: "very happy" → "happy"）
            for keyword, mood in LASTFM_TAG_TO_MOOD.items():
                if keyword in tag or tag in keyword:
                    mood_scores[mood] = mood_scores.get(mood, 0) + 5
        
        if mood_scores:
            best_mood = max(mood_scores, key=mood_scores.get)
            logger.info(f"  → Last.fmタグから推測: {best_mood} (スコア: {mood_scores[best_mood]})")
            return best_mood
        
        return None

class FileHandler:
    @staticmethod
    def safe_file_operation(func, *args, **kwargs):
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except (IOError, OSError) as e:
                if "Too many open files" in str(e):
                    time.sleep(2 ** attempt)
                    gc.collect()
                    continue
                raise
        raise Exception(f"ファイル操作が{max_attempts}回失敗")

def validate_audio_file(filepath: str) -> bool:
    try:
        if os.path.getsize(filepath) < 1024:
            return False
        if not os.access(filepath, os.R_OK):
            return False
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            audio_file = File(filepath)
            if audio_file is None:
                return False
        return True
    except:
        return False

def get_metadata_robust(filepath: str) -> Dict[str, str]:
    def _extract_metadata():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            audio = File(filepath)
            if audio is None:
                return {'title': 'Unknown', 'artist': 'Unknown', 'composer': 'Unknown', 
                        'conductor': 'Unknown', 'performer': 'Unknown', 'genre': 'Unknown', 
                        'album': 'Unknown', 'date': 'Unknown'}
            
            # タグ候補キーのリスト（形式ごとに複数キーを試す）
            TITLE_KEYS = ['title', 'TIT2', '©nam', 'name', 'title;eng', 'wm/title', 'TITLE']
            ARTIST_KEYS = ['artist', 'TPE1', '©ART', 'author', 'artist;eng', 'wm/artist', 'ARTIST', 'albumartist']
            COMPOSER_KEYS = ['composer', 'TCOM', 'COMPOSER', 'wm/composer']
            CONDUCTOR_KEYS = ['conductor', 'TPE3', 'CONDUCTOR', 'wm/conductor']
            PERFORMER_KEYS = ['performer', 'TPE3', 'PERFORMER', 'wm/performer']
            GENRE_KEYS = ['genre', 'TCON', 'GENRE', 'wm/genre']
            ALBUM_KEYS = ['album', 'TALB', 'ALBUM', 'wm/albumtitle']
            DATE_KEYS = ['date', 'TDRC', 'YEAR', 'wm/year', 'wm/recordingyear']
            
            # audio.tags を dict 形式のキー→値 に変換（小文字キー）
            tags_map = {}
            try:
                tags = audio.tags
                if tags:
                    # mutagen の Tag は dict-like、キーが tuple やカスタムオブジェクトの場合があるため文字列化
                    for k in getattr(tags, 'keys', lambda: [])():
                        try:
                            v = tags.get(k)
                        except Exception:
                            # tags[k] のスタイル
                            try:
                                v = tags[k]
                            except Exception:
                                v = None
                        if v is None:
                            continue
                        tags_map[str(k).lower()] = v
            except Exception:
                # 最悪の場合、tags_map は空のまま
                tags_map = {}
            
            # 汎用的な取得ルーチン
            def safe_get(possible_keys, default='Unknown'):
                # 1) 直接キー一致（lower化）
                for key in possible_keys:
                    if key is None:
                        continue
                    k = str(key).lower()
                    if k in tags_map:
                        val = tags_map[k]
                        if isinstance(val, (list, tuple)):
                            val = val[0] if val else None
                        if val:
                            return str(val).strip()
                # 2) 部分一致（キー名に候補が含まれている場合）
                for key in possible_keys:
                    if key is None:
                        continue
                    klow = str(key).lower()
                    for tk, tv in tags_map.items():
                        if klow in tk or tk in klow:
                            val = tv
                            if isinstance(val, (list, tuple)):
                                val = val[0] if val else None
                            if val:
                                return str(val).strip()
                # 3) mutagen の標準的 get() を試す（例: MP4 tags など）
                try:
                    for key in possible_keys:
                        if hasattr(audio, 'tags') and audio.tags:
                            v = audio.tags.get(key)
                            if v:
                                if isinstance(v, (list, tuple)):
                                    v = v[0]
                                return str(v).strip()
                except Exception:
                    pass
                return default

            # 各フィールド取得・正規化
            title = safe_get(TITLE_KEYS)
            artist = safe_get(ARTIST_KEYS)
            composer = safe_get(COMPOSER_KEYS)
            conductor = safe_get(CONDUCTOR_KEYS)
            performer = safe_get(PERFORMER_KEYS)
            genre = safe_get(GENRE_KEYS)
            album = safe_get(ALBUM_KEYS)
            date = safe_get(DATE_KEYS)

            return {
                'title': title or 'Unknown',
                'artist': artist or 'Unknown',
                'composer': normalize_composer_name(composer),
                'conductor': normalize_composer_name(conductor) if conductor and conductor != 'Unknown' else 'Unknown',
                'performer': normalize_performer_name(performer),
                'genre': normalize_genre_name(genre),
                'album': album or 'Unknown',
                'date': date or 'Unknown'
            }
    
    try:
        return FileHandler.safe_file_operation(_extract_metadata)
    except:
        return {'title': 'Unknown', 'artist': 'Unknown', 'composer': 'Unknown', 
                'conductor': 'Unknown', 'performer': 'Unknown', 'genre': 'Unknown', 
                'album': 'Unknown', 'date': 'Unknown'}

def extract_features_robust(filepath: str) -> Dict[str, float]:
    try:
        y, sr = librosa.load(filepath, duration=20, sr=22050, mono=True)
        features = {}
        try:
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            features['tempo'] = float(tempo) if tempo > 0 else 120.0
        except:
            features['tempo'] = 120.0
        try:
            rms = librosa.feature.rms(y=y)
            features['rms_mean'] = float(np.mean(rms))
        except:
            features['rms_mean'] = 0.01
        try:
            centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
            features['spectral_centroid'] = float(np.mean(centroid))
        except:
            features['spectral_centroid'] = 2000.0
        try:
            contrast = librosa.feature.spectral_contrast(y=y, sr=sr)
            features['spectral_contrast'] = float(np.mean(contrast))
        except:
            features['spectral_contrast'] = 20.0
        try:
            zcr = librosa.feature.zero_crossing_rate(y)
            features['zero_crossing_rate'] = float(np.mean(zcr))
        except:
            features['zero_crossing_rate'] = 0.05
        return features
    except:
        return {'tempo': 120.0, 'rms_mean': 0.01, 'spectral_centroid': 2000.0, 
                'spectral_contrast': 20.0, 'zero_crossing_rate': 0.05}

def classify_mood_enhanced(features: Dict[str, float], genre: str = None, api_mood: str = None) -> str:
    """拡張版ムード分類（Last.fm APIを最優先）"""
    
    # 1. Last.fm APIから取得したムードを最優先
    if api_mood and api_mood != 'neutral':
        logger.info(f"  ✓ APIムード採用: {api_mood}")
        return api_mood
    
    # 2. 音響特徴量から推測
    tempo = features.get('tempo', 120.0)
    energy = features.get('rms_mean', 0.01)
    brightness = features.get('spectral_centroid', 2000.0)
    contrast = features.get('spectral_contrast', 20.0)
    zcr = features.get('zero_crossing_rate', 0.05)
    
    genre_lower = genre.lower() if genre and genre != 'Unknown' else ''
    
    # 3. ジャンル別デフォルト（APIが無い場合）
    if genre_lower:
        for genre_key, default_moods in GENRE_DEFAULT_MOODS.items():
            if genre_key in genre_lower:
                # そのジャンルの特性に基づいて選択
                if tempo > 130:
                    return default_moods[1] if len(default_moods) > 1 else default_moods
# music_analyzer_enhanced.py の続き（前のファイルの末尾に追加してください）

                if tempo > 130 and energy > 0.03:
                    return default_moods[1] if len(default_moods) > 1 else default_moods[0]
                elif energy < 0.02:
                    return default_moods[0]
                else:
                    return default_moods[0]
    
    # 4. 音響特徴量による詳細な分類（より細かく）
    
    # 超ハイエナジー（aggressive, intense系）
    if energy > 0.05 and zcr > 0.12:
        return 'aggressive'
    elif energy > 0.045 and contrast > 25:
        return 'intense'
    
    # ハイエナジー × ハイテンポ（energetic, powerful系）
    if tempo > 140 and energy > 0.035:
        if brightness > 3000:
            return 'uplifting'
        elif contrast > 22:
            return 'powerful'
        else:
            return 'energetic'
    
    # ハイテンポ × 明るい（happy, upbeat系）
    if tempo > 120 and brightness > 2500:
        if energy > 0.03:
            return 'happy'
        elif energy > 0.025:
            return 'upbeat'
        else:
            return 'cheerful'
    
    # ミディアムテンポ × グルーヴ（groovy, funky系）
    if 95 < tempo < 125 and energy > 0.025:
        if zcr > 0.08:
            return 'funky'
        elif brightness > 2200:
            return 'groovy'
        else:
            return 'rhythmic'
    
    # ローテンポ × ダーク（melancholy, dark系）
    if tempo < 85 and brightness < 1800:
        if energy < 0.015:
            return 'somber'
        elif energy < 0.025:
            return 'melancholy'
        else:
            return 'dark'
    
    # ローテンポ × 穏やか（calm, peaceful系）
    if tempo < 90 and energy < 0.02:
        if brightness > 2000:
            return 'peaceful'
        elif brightness > 1600:
            return 'calm'
        else:
            return 'serene'
    
    # ローエナジー × 幻想的（ethereal, dreamy系）
    if energy < 0.018 and brightness > 2500:
        if contrast < 18:
            return 'ethereal'
        else:
            return 'dreamy'
    
    # ミディアムエナジー × スムーズ（smooth, mellow系）
    if 0.02 < energy < 0.035:
        if tempo < 100:
            if brightness > 2000:
                return 'smooth'
            else:
                return 'mellow'
        else:
            return 'moderate'
    
    # アンビエント・大気的
    if energy < 0.015 and contrast < 18:
        if brightness > 2200:
            return 'atmospheric'
        else:
            return 'ambient'
    
    # ドラマチック（dynamic range重視）
    if contrast > 28:
        return 'dramatic'
    elif contrast > 24:
        return 'epic'
    
    # その他の特徴的パターン
    if tempo > 115 and energy > 0.028:
        return 'energizing'
    elif brightness > 3200:
        return 'bright'
    elif tempo < 95 and energy > 0.025:
        return 'tender'
    
    # デフォルト（最後の手段）
    if energy > 0.025:
        return 'moderate'
    else:
        return 'calm'

def enrich_metadata_with_apis(metadata: Dict[str, str], mb_api: MusicBrainzAPI, lastfm_api: LastFmAPI) -> Tuple[Dict[str, str], Optional[str]]:
    """APIでメタデータを補完し、ムードを取得"""
    artist = metadata.get('artist', 'Unknown')
    title = metadata.get('title', 'Unknown')
    enriched_metadata = metadata.copy()
    api_mood = None
    
    # MusicBrainzから作曲家・指揮者情報を取得
    mb_data = mb_api.search_recording(artist, title)
    if mb_data:
        if enriched_metadata.get('composer') == 'Unknown' and mb_data.get('composer'):
            enriched_metadata['composer'] = normalize_composer_name(mb_data['composer'])
        if enriched_metadata.get('conductor') == 'Unknown' and mb_data.get('conductor'):
            enriched_metadata['conductor'] = normalize_composer_name(mb_data['conductor'])
    
    # Last.fmからタグとムード情報を取得
    lastfm_data = lastfm_api.get_track_info(artist, title)
    if lastfm_data and lastfm_data.get('tags'):
        api_mood = lastfm_api.infer_mood_from_tags(lastfm_data['tags'])
        logger.info(f"  → Last.fm推測ムード: {api_mood}")
    
    return enriched_metadata, api_mood

class TrackProcessingTimeout(Exception):
    """SMB/NAS等のネットワークマウントで応答が固まった際に発生させる例外"""
    pass

def _timeout_handler(signum, frame):
    raise TrackProcessingTimeout()

def process_single_track_safe(filepath: str, mb_api: MusicBrainzAPI = None,
                               lastfm_api: LastFmAPI = None,
                               timeout: int = ANALYSIS_TIMEOUT,
                               max_retries: int = MAX_RETRIES) -> Optional[Dict]:
    """
    process_single_trackをタイムアウト・リトライ付きで実行するラッパー。

    Soundgenic等のSMBマウント上では、接続の瞬断や応答遅延で
    librosa.load()やファイル読み込みが例外を出さずに固まる(hang)ことがある。
    signal.alarmで強制的に打ち切り、一時的なネットワーク不調ならリトライし、
    改善しなければそのファイルだけスキップして全体のスキャンは継続する。
    """
    last_error = None

    for attempt in range(1, max_retries + 1):
        # SIGALRMはメインスレッド・Unix系のみで有効（Qji開発環境のLinuxを想定）
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout)
        try:
            result = process_single_track(filepath, mb_api, lastfm_api)
            signal.alarm(0)
            return result
        except TrackProcessingTimeout:
            last_error = f"タイムアウト({timeout}秒)"
            logger.warning(f"⏱️ [{attempt}/{max_retries}] {os.path.basename(filepath)} - {last_error}。ネットワークマウントの応答遅延の可能性があります")
        except (OSError, IOError) as e:
            last_error = f"I/Oエラー: {e}"
            logger.warning(f"🔌 [{attempt}/{max_retries}] {os.path.basename(filepath)} - {last_error}（SMB接続の瞬断の可能性）")
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)

        if attempt < max_retries:
            time.sleep(2 * attempt)  # 再接続の猶予を持たせて段階的に待つ

    logger.error(f"❌ {filepath} - {max_retries}回試行後もスキップ（最終エラー: {last_error}）")
    return None

def process_single_track(filepath: str, mb_api: MusicBrainzAPI = None, lastfm_api: LastFmAPI = None) -> Optional[Dict]:
    """単一楽曲の処理（ファイルハンドル管理改善）"""
    audio = None
    y = None
    
    try:
        if not validate_audio_file(filepath):
            return None
        
        # メタデータ取得
        metadata = get_metadata_robust(filepath)
        
        # API連携でメタデータ補完 + ムード取得
        api_mood = None
        if mb_api and lastfm_api:
            logger.info(f"🔍 API検索: {metadata['artist']} - {metadata['title']}")
            metadata, api_mood = enrich_metadata_with_apis(metadata, mb_api, lastfm_api)
        
        # 音響特徴量抽出
        features = extract_features_robust(filepath)
        
        # ムード分類（APIムードを最優先）
        mood = classify_mood_enhanced(features, metadata['genre'], api_mood)
        
        return {
            'path': filepath,
            'title': metadata['title'],
            'artist': metadata['artist'],
            'composer': metadata['composer'],
            'conductor': metadata['conductor'],
            'performer': metadata['performer'],
            'genre': metadata['genre'],
            'album': metadata.get('album', 'Unknown'),
            'features': features,
            'mood': mood,
            'api_mood': api_mood,
            'processed_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"処理エラー: {filepath} - {e}")
        return None
    finally:
        # メモリ解放
        if audio is not None:
            del audio
        if y is not None:
            del y
        gc.collect()

BACKUP_DIR = os.path.expanduser('~/.music_analyzer2_backups')
BACKUP_GENERATIONS = 10       # 世代バックアップを何世代分残すか
SHRINK_GUARD_RATIO = 0.5      # 既存DBよりこの割合以上少なくなる保存は危険とみなす
LOCK_FILE = os.path.expanduser('~/.music_analyzer2.lock')


class DatabaseShrinkGuardError(Exception):
    """保存しようとしているDBが既存DBより大幅に小さい場合に発生させる例外"""
    pass


def _rotate_generational_backup():
    """
    DATABASE_FILEを世代バックアップとして保存する。
    従来は単一の .backup ファイルを毎回上書きしていたため、
    連続保存（BACKUP_INTERVALごとの中間保存など）が続くと
    数世代前の"本当の元データ"がすぐに失われていた。
    タイムスタンプ付きで複数世代残すことで、
    「上書きに気づくのが遅れた」場合でも遡って復元できるようにする。
    """
    if not os.path.exists(DATABASE_FILE):
        return
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts = time.strftime('%Y%m%d_%H%M%S')
        dest = os.path.join(BACKUP_DIR, f"music_mood_db_{ts}.json")
        import shutil
        shutil.copy2(DATABASE_FILE, dest)

        # 従来互換の .backup も一応残す（直近1世代分、既存ツールが参照する場合用）
        shutil.copy2(DATABASE_FILE, f"{DATABASE_FILE}.backup")

        # 古い世代を整理（直近 BACKUP_GENERATIONS 世代だけ残す）
        backups = sorted(
            f for f in os.listdir(BACKUP_DIR)
            if f.startswith("music_mood_db_") and f.endswith(".json")
        )
        for old in backups[:-BACKUP_GENERATIONS]:
            try:
                os.remove(os.path.join(BACKUP_DIR, old))
            except OSError:
                pass
    except Exception as e:
        logger.warning(f"⚠️ 世代バックアップの作成に失敗しました: {e}")


def save_database_safely(db: List[Dict], backup: bool = False,
                          allow_shrink: bool = False) -> bool:
    """
    データベースの安全な保存。

    変更点:
      - .backupを毎回上書きする方式をやめ、タイムスタンプ付き世代バックアップに変更
        （直近10世代を保持。これにより「連続保存でバックアップ自体が
        上書きされ続けて元データが追えなくなる」問題を解消）
      - 既存DBより大幅に（デフォルト50%以上）件数が減る保存は、
        allow_shrink=True を明示しない限り拒否する（誤った--forceや
        スキャン範囲の縮小による無自覚な大量削除を防ぐ）
    """
    try:
        if os.path.exists(DATABASE_FILE):
            try:
                with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                    existing_count = len(json.load(f))
            except Exception:
                existing_count = 0

            if existing_count > 0 and not allow_shrink:
                new_count = len(db)
                if new_count < existing_count * SHRINK_GUARD_RATIO:
                    raise DatabaseShrinkGuardError(
                        f"保存しようとしている内容は{new_count}曲ですが、"
                        f"現在のデータベースには{existing_count}曲あります。"
                        f"{int(SHRINK_GUARD_RATIO*100)}%以上の減少は誤操作の"
                        f"可能性が高いため、保存を中止しました。"
                    )

        if backup:
            _rotate_generational_backup()

        with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        return True
    except DatabaseShrinkGuardError as e:
        logger.error(f"🛑 保存を中止しました（データ減少ガード作動）: {e}")
        return False
    except Exception as e:
        logger.error(f"保存エラー: {e}")
        return False

def find_music_directories():
    """音楽ディレクトリを自動検出"""
    potential_dirs = []
    for base_dir in MUSIC_DIRS:
        if os.path.exists(base_dir) and os.path.isdir(base_dir):
            potential_dirs.append(base_dir)
    return list(set(potential_dirs))

def normalize_existing_database():
    """既存データベースの正規化"""
    logger.info("📄 既存データベースの正規化を開始")
    if not os.path.exists(DATABASE_FILE):
        logger.error(f"データベースファイルが見つかりません: {DATABASE_FILE}")
        return
    
    try:
        with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
            database = json.load(f)
        logger.info(f"データベース読み込み: {len(database)}曲")
        
        updated_count = 0
        for entry in database:
            old_composer = entry.get('composer', 'Unknown')
            old_conductor = entry.get('conductor', 'Unknown')
            old_performer = entry.get('performer', 'Unknown')
            old_genre = entry.get('genre', 'Unknown')
            
            new_composer = normalize_composer_name(old_composer)
            new_conductor = normalize_composer_name(old_conductor) if old_conductor != 'Unknown' else 'Unknown'
            new_performer = normalize_performer_name(old_performer)
            new_genre = normalize_genre_name(old_genre)
            
            if new_composer != old_composer:
                entry['composer'] = new_composer
                updated_count += 1
            if new_conductor != old_conductor and old_conductor != 'Unknown':
                entry['conductor'] = new_conductor
                updated_count += 1
            if new_performer != old_performer and old_performer != 'Unknown':
                entry['performer'] = new_performer
                updated_count += 1
            if new_genre != old_genre:
                entry['genre'] = new_genre
                updated_count += 1
        
        if updated_count > 0:
            if save_database_safely(database, backup=True):
                logger.info(f"✅ {updated_count}件を正規化しました")
        else:
            logger.info("✅ 正規化が必要な項目はありませんでした")
            
    except Exception as e:
        logger.error(f"正規化処理エラー: {e}")

def cleanup_missing_files() -> int:
    """データベースから存在しないファイルを削除する"""
    logger.info("🧹 存在しないファイルのクリーンアップを開始")
    if not os.path.exists(DATABASE_FILE):
        logger.error(f"データベースファイルが見つかりません: {DATABASE_FILE}")
        return 0
    
    try:
        with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
            database = json.load(f)
        
        original_count = len(database)
        logger.info(f"データベース読み込み: {original_count}曲")
        
        valid_entries = []
        removed_entries = []
        for entry in database:
            path = entry.get('path', '')
            if os.path.exists(path):
                valid_entries.append(entry)
            else:
                removed_entries.append(path)
                logger.info(f"  🗑️ 削除: {path}")
        
        removed_count = len(removed_entries)
        if removed_count > 0:
            missing_ratio = removed_count / original_count if original_count else 0

            warning_extra = ""
            if missing_ratio > 0.3:
                warning_extra = (
                    f"\n   ⚠️ 全体の{missing_ratio*100:.0f}%が「見つからない」判定です。"
                    f"これはファイルが本当に削除されたのではなく、NASのマウントが"
                    f"外れている・ネットワークが切断されている可能性があります。"
                    f"続行する前に、マウント状態を確認することを強くおすすめします。"
                )

            if not confirm_action(
                f"{removed_count}曲をデータベースから削除しようとしています"
                f"（現在{original_count}曲 → 削除後{len(valid_entries)}曲）。"
                f"{warning_extra}"
            ):
                logger.info("🛑 クリーンアップを中止しました（データベースは変更されていません）")
                return 0

            if save_database_safely(valid_entries, backup=True):
                logger.info(f"✅ クリーンアップ完了: {removed_count}曲を削除（残り {len(valid_entries)}曲）")
            else:
                logger.error("データベースの保存に失敗しました")
        else:
            logger.info("✅ 削除対象のファイルはありませんでした")
        
        return removed_count
    
    except Exception as e:
        logger.error(f"クリーンアップ処理エラー: {e}")
        return 0

def build_music_database_improved(custom_dirs=None, force_rescan=False, use_apis=True, lastfm_key=None):
    """改良版データベース構築（ファイルハンドル管理改善）"""
    logger.info("🎵 拡張版音楽データベース構築開始（Last.fm API最大活用）")
    
    # リソース制限緩和
    try:
        import resource
        soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
        new_limit = min(8192, hard)
        resource.setrlimit(resource.RLIMIT_NOFILE, (new_limit, hard))
        logger.info(f"ファイルハンドル制限: {soft} → {new_limit}")
    except Exception as e:
        logger.warning(f"リソース制限調整失敗: {e}")
    
    # API初期化
    api_cache = APICache()
    mb_api = MusicBrainzAPI(api_cache) if use_apis else None
    lastfm_api = LastFmAPI(lastfm_key or LASTFM_API_KEY, api_cache) if use_apis else None
    
    if use_apis:
        logger.info("✓ MusicBrainz API: 有効")
        logger.info("✓ Last.fm API: 有効（ムード検出強化）")
    
    # ディレクトリ検索
    music_directories = custom_dirs if custom_dirs else find_music_directories()
    
    # 既存DB読み込み
    existing_db = {}

    if force_rescan:
        # --force は既存データベースを一切参照せず、今回スキャンした範囲だけで
        # DBを丸ごと再構築する。過去にこの確認なしで実行し、スキャン範囲外の
        # 既存データが大量に失われる事故が実際に起きたため、必ず確認する。
        prior_count = 0
        if os.path.exists(DATABASE_FILE):
            try:
                with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                    prior_count = len(json.load(f))
            except Exception:
                prior_count = 0

        if prior_count > 0 and not confirm_action(
            f"--force が指定されています。現在のデータベースには{prior_count}曲"
            f"登録されていますが、--force は既存データを読み込まず、"
            f"今回スキャンする範囲（{', '.join(music_directories)}）だけで"
            f"データベースを丸ごと作り直します。今回のスキャン範囲に含まれない"
            f"曲の情報はすべて失われます。"
        ):
            logger.info("🛑 処理を中止しました（データベースは変更されていません）")
            return
    elif os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                existing_db = {item['path']: item for item in existing_data}
            logger.info(f"既存DB読み込み: {len(existing_db)}曲")
            # 存在しないファイルをDBから除去（ただし必ず確認する。
            # NASの一時的な切断でも「ファイルが存在しない」と判定されるため、
            # 確認なしで削除すると本当は消えていないファイルまで失う危険がある）
            missing_paths = [path for path in existing_db if not os.path.exists(path)]
            if missing_paths:
                missing_ratio = len(missing_paths) / len(existing_db) if existing_db else 0
                warning_extra = ""
                if missing_ratio > 0.3:
                    warning_extra = (
                        f" ⚠️ 全体の{missing_ratio*100:.0f}%が対象です。"
                        f"NASのマウントが外れているなど、一時的な問題の可能性があります。"
                    )
                if confirm_action(
                    f"{len(missing_paths)}曲がディスク上に見つからないため、"
                    f"データベースから除去しようとしています。{warning_extra}"
                ):
                    logger.info(f"🗑️ 存在しないファイルをDBから除去: {len(missing_paths)}曲")
                    for path in missing_paths:
                        logger.info(f"  削除: {path}")
                        del existing_db[path]
                    logger.info(f"  残り: {len(existing_db)}曲")
                else:
                    logger.info("🛑 見つからないファイルの除去をスキップしました（DBに残したまま続行）")
        except Exception as e:
            logger.error(f"既存DB読み込みエラー: {e}")
    
    # ファイル収集
    all_files = []
    for directory in music_directories:
        if os.path.exists(directory):
            logger.info(f"📁 スキャン中: {directory}")
            try:
                for root, _, files in os.walk(directory, onerror=NETWORK_WALK_ERROR_HANDLER):
                    for file in files:
                        if file.lower().endswith(SUPPORTED_EXTENSIONS):
                            all_files.append(os.path.join(root, file))
            except (OSError, IOError) as e:
                logger.warning(f"⚠️ {directory} のスキャン中にネットワークエラーが発生、このディレクトリをスキップして続行: {e}")
                continue
    
    files_to_process = [f for f in all_files if force_rescan or f not in existing_db]
    new_database = list(existing_db.values())
    
    logger.info(f"処理対象: {len(files_to_process)}曲（既存: {len(existing_db)}曲）")
    
    # 処理開始
    success_count = 0
    error_count = 0
    
    for i, filepath in enumerate(files_to_process, 1):
        try:
            logger.info(f"[{i}/{len(files_to_process)}] 処理中: {os.path.basename(filepath)}")
            result = process_single_track_safe(filepath, mb_api, lastfm_api)
            
            if result:
                new_database.append(result)
                success_count += 1
                logger.info(f"  ✅ ムード: {result['mood']}")
            else:
                error_count += 1
            
            # 定期的にDB保存（50曲ごと）
            if i % BACKUP_INTERVAL == 0:
                logger.info(f"💾 中間保存中... ({len(new_database)}曲)")
                save_database_safely(new_database, backup=True)
                
                # キャッシュも保存
                if use_apis:
                    api_cache.save_cache(force=True)
                
                # メモリクリーンアップ
                gc.collect()
                
                # 進捗表示
                logger.info(f"📊 進捗: 成功 {success_count}, エラー {error_count}")
        
        except KeyboardInterrupt:
            logger.info("⏸️ ユーザーによる中断")
            break
        except Exception as e:
            logger.error(f"予期しないエラー: {filepath} - {e}")
            error_count += 1
    
    # 最終保存
    logger.info("💾 最終保存中...")
    save_database_safely(new_database, backup=True)
    
    if use_apis:
        logger.info("💾 キャッシュ最終保存中...")
        api_cache.save_cache(force=True)
    
    logger.info(f"""
✅ 処理完了:
  - 総曲数: {len(new_database)}曲
  - 新規追加: {success_count}曲
  - エラー: {error_count}曲
  - データベース: {DATABASE_FILE}
""")
    
    # 統計表示
    show_mood_stats(new_database)

def show_mood_stats(db: List[Dict]):
    """ムード統計を表示"""
    mood_counts = {}
    api_mood_counts = {}
    
    for track in db:
        mood = track.get('mood', 'unknown')
        mood_counts[mood] = mood_counts.get(mood, 0) + 1
        
        if track.get('api_mood'):
            api_mood_counts[mood] = api_mood_counts.get(mood, 0) + 1
    
    total = len(db)
    if total == 0:
        return
    
    print("\n📊 ムード分布（拡張版）:")
    for mood, count in sorted(mood_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total) * 100
        api_count = api_mood_counts.get(mood, 0)
        api_ratio = (api_count / count * 100) if count > 0 else 0
        bar = "█" * max(1, int(percentage / 2))
        print(f"  {mood:15}: {count:4}曲 ({percentage:5.1f}%) {bar} [API: {api_ratio:.0f}%]")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='拡張版音楽ムード分析（Last.fm API最大活用）')
    parser.add_argument('command', nargs='?', choices=['add', 'normalize', 'stats', 'cleanup'])
    parser.add_argument('add_dirs', nargs='*')
    parser.add_argument('--dirs', nargs='+')
    parser.add_argument('--force', action='store_true', help='全ファイルを再スキャン')
    parser.add_argument('--no-api', action='store_true', help='API使用を無効化')
    parser.add_argument('--lastfm-key', type=str, help='Last.fm APIキー')
    parser.add_argument('--no-wait', action='store_true', help='終了時のEnter待ちをスキップ（シェルスクリプトから呼ぶ場合）')
    parser.add_argument('--yes', action='store_true',
                         help='削除・上書き等の確認プロンプトをすべて自動承認する（自動化用。通常は使わないこと）')
    parser.add_argument('--db-file', type=str,
                         help='使用するデータベースファイルのパス（省略時は~/music_mood_db.json。'
                              'テスト実行時は必ず本番と別のパスを指定すること）')
    args = parser.parse_args()

    if args.yes:
        AUTO_CONFIRM = True
        logger.warning("⚠️ --yes が指定されています。削除・上書きの確認はすべて自動承認されます。")

    if args.db_file:
        DATABASE_FILE = os.path.expanduser(args.db_file)
        logger.info(f"📄 データベースファイル: {DATABASE_FILE}")

    # 同時実行防止ロック
    # 過去に「別プロセスで同時実行したら片方の作業が消えた」事故が実際に起きたため、
    # 同じDATABASE_FILEに対して複数のプロセスが同時に書き込むことを防ぐ。
    lock_path = f"{DATABASE_FILE}.lock"
    lock_fd = None
    try:
        import fcntl
        lock_fd = open(lock_path, 'w')
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            lock_fd.write(str(os.getpid()))
            lock_fd.flush()
        except BlockingIOError:
            try:
                with open(lock_path, 'r') as f:
                    other_pid = f.read().strip()
            except Exception:
                other_pid = "不明"
            print(f"❌ 既に別のプロセス（PID: {other_pid}）が同じデータベース"
                  f"（{DATABASE_FILE}）に対して実行中です。同時実行はデータ破損の"
                  f"原因になるため中止しました。他のプロセスの終了を待ってから"
                  f"再実行してください。")
            sys.exit(1)
    except ImportError:
        # fcntlが使えない環境（Windows等）ではロックをスキップ
        logger.warning("⚠️ このOSではファイルロックが使えないため、同時実行チェックをスキップします")

    try:
        if args.command == 'normalize':
            normalize_existing_database()
        elif args.command == 'stats':
            if os.path.exists(DATABASE_FILE):
                with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                    db = json.load(f)
                show_mood_stats(db)
            else:
                print("データベースが見つかりません")
        elif args.command == 'cleanup':
            cleanup_missing_files()
        else:
            custom_dirs = None
            if args.command == 'add' and args.add_dirs:
                custom_dirs = find_music_directories() + args.add_dirs
            elif args.dirs:
                custom_dirs = args.dirs

            build_music_database_improved(
                custom_dirs=custom_dirs,
                force_rescan=args.force,
                use_apis=not args.no_api,
                lastfm_key=args.lastfm_key
            )
    finally:
        if lock_fd is not None:
            try:
                import fcntl
                fcntl.flock(lock_fd, fcntl.LOCK_UN)
                lock_fd.close()
                os.remove(lock_path)
            except Exception:
                pass


    # --no-wait が指定された場合はEnter待ちなしで終了（bash側で処理）
    if not args.no_wait:
        try:
            input("\n✅ 処理が完了しました。Enterキーを押すと終了します...")
        except (EOFError, KeyboardInterrupt):
            pass
    sys.exit(0)