import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from PIL import Image

# Register bin/ directories in PATH environment so binaries (yt-dlp, ffmpeg, aria2c) are discovered reliably
def _setup_bin_path():
    candidate_dirs = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin"),
        os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "bin"),
        os.path.join(os.getcwd(), "bin"),
    ]
    if hasattr(sys, "_MEIPASS"):
        candidate_dirs.insert(0, os.path.join(sys._MEIPASS, "bin"))

    for b_dir in candidate_dirs:
        if os.path.isdir(b_dir):
            abs_b = os.path.abspath(b_dir)
            current_path = os.environ.get("PATH", "")
            if abs_b not in current_path:
                os.environ["PATH"] = abs_b + os.pathsep + current_path

_setup_bin_path()


def get_bin_executable(binary_name):
    """Locate the absolute path of an executable binary (yt-dlp, ffmpeg, aria2c) across search paths."""
    _setup_bin_path()
    exe_name = f"{binary_name}.exe" if sys.platform == "win32" and not binary_name.lower().endswith(".exe") else binary_name

    candidate_dirs = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin"),
        os.path.join(os.path.dirname(os.path.abspath(sys.executable)), "bin"),
        os.path.join(os.getcwd(), "bin"),
    ]
    if hasattr(sys, "_MEIPASS"):
        candidate_dirs.insert(0, os.path.join(sys._MEIPASS, "bin"))

    for c_dir in candidate_dirs:
        target = os.path.join(c_dir, exe_name)
        if os.path.isfile(target):
            return target

    # Fallback to system PATH lookup
    found = shutil.which(binary_name) or shutil.which(exe_name)
    if found:
        return found

    return binary_name


CONFIG_FILE = "config.json"
HISTORY_FILE = "history.json"
CACHE_DIR = os.path.join(".cache", "covers")

DEFAULT_CONFIG = {
    "download_dir": "downloads",
    "use_detailed_filename": False,
    "default_id": "RJ01673437",
    "connections": 16,
    "notify_popup": True,
    "auto_clipboard": True,
    "ytdlp_channel": "stable",
    "audio_format": "auto",
    "language": "auto",
}


def get_ytdlp_version():
    """Query the installed version string of the yt-dlp binary."""
    import subprocess
    ytdlp_bin = get_bin_executable("yt-dlp")
    try:
        res = subprocess.run(
            [ytdlp_bin, "--version"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            timeout=10,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
        return "Unknown"
    except Exception:
        return "Not found"


def update_ytdlp_engine(channel="stable"):
    """
    Update the yt-dlp binary to the stable or nightly release channel (@latest).

    Returns:
        tuple: (success: bool, status_code: str, display_message: str)
        status_code is one of: 'already_latest', 'updated', or 'error'.
    """
    import subprocess
    target_channel = channel.strip().lower()
    if target_channel not in ["stable", "nightly"]:
        target_channel = "stable"

    ytdlp_bin = get_bin_executable("yt-dlp")
    # Use @latest to allow channel switching or downgrades (e.g., nightly to stable)
    cmd = [ytdlp_bin, "--update-to", f"{target_channel}@latest"]
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            timeout=120,
        )
        raw_out = (res.stdout or "").strip()
        raw_err = (res.stderr or "").strip()
        combined = f"{raw_out}\n{raw_err}".lower()

        cur_ver = get_ytdlp_version()

        if res.returncode != 0:
            err_msg = raw_err or raw_out or f"Proses update gagal (exit code: {res.returncode})."
            return False, "error", f"Gagal memperbarui yt-dlp: {err_msg}"

        if "is up to date" in combined:
            clean_msg = f"yt-dlp sudah menggunakan versi terbaru ({cur_ver}) pada channel {target_channel.title()}."
            return True, "already_latest", clean_msg
        else:
            clean_msg = f"Berhasil memperbarui yt-dlp ke versi {cur_ver} (Channel: {target_channel.title()})."
            return True, "updated", clean_msg
    except Exception as e:
        return False, "error", f"Gagal menjalankan pembaruan: {e}"


def get_dir_size_str(dir_path):
    """Calculate the total file size in a directory formatted as MB or KB."""
    if not os.path.exists(dir_path):
        return "0 KB"
    total_bytes = 0
    for root, _, files in os.walk(dir_path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total_bytes += os.path.getsize(fp)
            except OSError:
                pass
    if total_bytes > 1024 * 1024:
        return f"{total_bytes / (1024 * 1024):.2f} MB"
    elif total_bytes > 1024:
        return f"{total_bytes / 1024:.1f} KB"
    else:
        return f"{total_bytes} B"


def get_cache_size_info():
    """Return storage statistics for cover cache and temporary cache folders."""
    covers_dir = os.path.join(".cache", "covers")
    temp_dir = os.path.join(".cache", "temp")
    
    cover_files_count = len(os.listdir(covers_dir)) if os.path.exists(covers_dir) else 0
    temp_files_count = len(os.listdir(temp_dir)) if os.path.exists(temp_dir) else 0

    return {
        "covers_size": get_dir_size_str(covers_dir),
        "covers_count": cover_files_count,
        "temp_size": get_dir_size_str(temp_dir),
        "temp_count": temp_files_count,
    }


def clear_cover_cache():
    """Remove all cached cover image files from .cache/covers/."""
    covers_dir = os.path.join(".cache", "covers")
    if os.path.exists(covers_dir):
        for f in os.listdir(covers_dir):
            fp = os.path.join(covers_dir, f)
            try:
                if os.path.isfile(fp):
                    os.remove(fp)
            except OSError:
                pass


def clear_temp_cache():
    """Remove all residual temporary and partial download files from .cache/temp/."""
    temp_dir = os.path.join(".cache", "temp")
    if os.path.exists(temp_dir):
        for f in os.listdir(temp_dir):
            fp = os.path.join(temp_dir, f)
            try:
                if os.path.isfile(fp):
                    os.remove(fp)
            except OSError:
                pass


def clear_all_history():
    """Clear all download history records from history.json."""
    save_history([])


def load_config():
    """Load configuration dictionary from config.json, ensuring default keys exist."""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            # Ensure all default keys are present
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(config_dict):
    """Persist configuration dictionary to config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save config.json: {e}")


def get_download_dir():
    """Retrieve configured download directory, creating it if it does not exist."""
    cfg = load_config()
    d_dir = cfg.get("download_dir", "downloads")
    os.makedirs(d_dir, exist_ok=True)
    return d_dir


def set_download_dir(new_dir):
    """Update the download directory path and save to config.json."""
    if not new_dir:
        return
    cfg = load_config()
    cfg["download_dir"] = new_dir
    save_config(cfg)
    os.makedirs(new_dir, exist_ok=True)


def get_audio_format():
    """Retrieve configured output audio format ('auto', 'm4a', or 'mp3')."""
    cfg = load_config()
    fmt = str(cfg.get("audio_format", "auto")).strip().lower()
    if fmt in ("auto", "smart", "default"):
        return "auto"
    return "m4a" if fmt in ("m4a", "aac") else "mp3"


def set_audio_format(fmt):
    """Save selected audio format preference ('auto', 'm4a', or 'mp3') to config.json."""
    raw = str(fmt).strip().lower()
    if raw in ("auto", "smart", "default"):
        clean_fmt = "auto"
    elif raw in ("m4a", "aac"):
        clean_fmt = "m4a"
    else:
        clean_fmt = "mp3"
    cfg = load_config()
    cfg["audio_format"] = clean_fmt
    save_config(cfg)


def get_app_language():
    """Retrieve UI language preference from config ('auto', 'en', 'id', 'ja', 'zh')."""
    cfg = load_config()
    return cfg.get("language", "auto")


def set_app_language(lang_code):
    """Save UI language preference to config.json and activate in-memory."""
    from i18n import set_active_language
    cfg = load_config()
    clean_code = str(lang_code).strip().lower()
    cfg["language"] = clean_code
    save_config(cfg)
    set_active_language(clean_code)


def load_history():
    """Load download history records from history.json."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(history_list):
    """Save download history records to history.json."""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history_list, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to save history.json: {e}")


def cache_cover_image(rjid, source_cover_path):
    """Generate and save a thumbnail cover image to .cache/covers/RJxxxxxx.jpg."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"{rjid}.jpg")
    try:
        with Image.open(source_cover_path) as img:
            img.thumbnail((320, 240))
            img.convert("RGB").save(cache_path, "JPEG", quality=85)
        return cache_path
    except Exception:
        # Fallback to standard copy if thumbnail generation fails
        try:
            shutil.copy2(source_cover_path, cache_path)
            return cache_path
        except Exception:
            return None


def add_to_history(rjid, title, cv, circle, cover_url, output_path, temp_cover_path=None, genre="-", age_rating="-"):
    """Append a newly completed download item to history.json and cache its cover image."""
    if temp_cover_path and os.path.exists(temp_cover_path):
        cache_cover_image(rjid, temp_cover_path)

    file_size_str = "0 MB"
    if os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        file_size_str = f"{size_mb:.1f} MB"

    entry = {
        "rjid": rjid,
        "title": title if title and title != "Memuat info..." else rjid,
        "cv": cv if cv else "-",
        "circle": circle if circle else "-",
        "genre": genre if genre else "-",
        "age_rating": age_rating if age_rating else "-",
        "cover_url": cover_url,
        "output_path": os.path.abspath(output_path),
        "download_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "file_size": file_size_str,
    }

    histories = load_history()
    histories = [h for h in histories if h.get("rjid") != rjid]
    histories.insert(0, entry)
    save_history(histories)


def check_url_exists(url, referer="https://japaneseasmr.com", user_agent="Mozilla/5.0"):
    """Verify HTTP accessibility of a remote resource URL (status 200 or 206)."""
    import urllib.request
    try:
        req = urllib.request.Request(
            url,
            headers={
                "Referer": referer,
                "User-Agent": user_agent,
                "Range": "bytes=0-10",
            },
        )
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            if resp.status in (200, 206):
                return True
    except Exception:
        pass
    return False


ASMRONE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Referer": "https://asmr.one/",
    "Origin": "https://asmr.one",
    "Accept-Language": "zh-CN,zh;q=0.9,ja;q=0.8,en;q=0.7",
}


def _natural_sort_key(s):
    import re
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]


def fetch_asmrone_tree(numeric_id):
    """Fetch track directory tree from asmr.one API with appropriate request headers."""
    import urllib.request
    url = f"https://api.asmr.one/api/tracks/{numeric_id}"
    req = urllib.request.Request(url, headers=ASMRONE_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=7) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception:
        pass
    return None


def filter_smart_asmrone_tracks(tree):
    """
    Filter and select primary narrative audio tracks from an asmr.one directory tree:
    1. Filter for valid audio file extensions.
    2. Select root numbered tracks if present.
    3. Prioritize main narrative folders ('本編' / 'main') over secondary variants (no-SE, raw, system sound).
    4. Prefer MP3 over large uncompressed WAV files when duplicates exist.
    5. Sort tracks using natural numerical order.
    """
    import re
    AUDIO_EXTS = ('.mp3', '.wav', '.m4a', '.flac', '.aac', '.ogg')

    def extract_audios_from_node(node):
        audios = []
        if node.get("type") == "audio" and (node.get("mediaStreamUrl") or node.get("mediaDownloadUrl")):
            t = node.get("title", "")
            if any(t.lower().endswith(ext) for ext in AUDIO_EXTS):
                audios.append({
                    "name": re.sub(r'\.[a-zA-Z0-9]+$', '', t),
                    "url": node.get("mediaDownloadUrl") or node.get("mediaStreamUrl"),
                    "title": t,
                    "referer": "https://asmr.one/",
                    "source": "asmr.one",
                    "duration": float(node.get("duration") or 0.0),
                })
        for c in node.get("children", []):
            audios.extend(extract_audios_from_node(c))
        return audios

    # 1. Collect all audio files available at the root level
    root_audios = []
    for item in tree:
        if item.get("type") == "audio" and (item.get("mediaStreamUrl") or item.get("mediaDownloadUrl")):
            title = item.get("title", "")
            if any(title.lower().endswith(ext) for ext in AUDIO_EXTS):
                root_audios.append({
                    "name": re.sub(r'\.[a-zA-Z0-9]+$', '', title),
                    "url": item.get("mediaDownloadUrl") or item.get("mediaStreamUrl"),
                    "title": title,
                    "referer": "https://asmr.one/",
                    "source": "asmr.one",
                    "duration": float(item.get("duration") or 0.0),
                })

    # Check whether root audios follow a numbered episodic sequence (01, 02, ...)
    numbered_root = [a for a in root_audios if re.match(r'^\s*0?\d+', a["title"])]
    if len(numbered_root) >= 2 or (len(root_audios) > 0 and len(numbered_root) == len(root_audios)):
        # If root audios are exclusively lossless WAV files, check for a dedicated MP3 folder for the main narrative
        if all(a["title"].lower().endswith((".wav", ".flac")) for a in numbered_root):
            for item in tree:
                if item.get("type") == "folder":
                    f_title = item.get("title", "")
                    if "本編" in f_title and "mp3" in f_title.lower():
                        c_audios = extract_audios_from_node(item)
                        mp3_only = [c for c in c_audios if c["title"].lower().endswith(".mp3")]
                        if len(mp3_only) >= 2:
                            mp3_only.sort(key=lambda x: _natural_sort_key(x["title"]))
                            return mp3_only

        numbered_root.sort(key=lambda x: _natural_sort_key(x["title"]))
        return numbered_root

    # 2. Score candidate subfolders if audio tracks are organized into directories
    folders = [item for item in tree if item.get("type") == "folder"]

    def folder_score(f_title):
        score = 0
        ft_lower = f_title.lower()
        if "本編" in f_title or "main" in ft_lower or "track" in ft_lower:
            score += 100
        if "おすすめ" in f_title or "お勧め" in f_title or "se有" in f_title or "seあり" in ft_lower:
            score += 50
        if "mp3" in ft_lower:
            score += 30
        penalties = ["se無し", "se無", "seなし", "nose", "音声原本", "原本", "システムボイス", "システム音", "効果音", "bgm", "昭和音質", "木枯らし", "雨降り", "se強化"]
        if any(neg in ft_lower for neg in penalties):
            score -= 80
        if "おまけ" in f_title and "本編" not in f_title:
            score -= 20
        return score

    folders.sort(key=lambda f: folder_score(f.get("title", "")), reverse=True)

    for best_f in folders:
        target_node = best_f
        while True:
            sub_children = [c for c in target_node.get("children", []) if c.get("type") == "folder"]
            if not sub_children:
                break
            sub_children.sort(key=lambda c: folder_score(c.get("title", "")), reverse=True)
            target_node = sub_children[0]

        tracks = extract_audios_from_node(target_node)
        if tracks:
            seen_bases = {}
            filtered = []
            for tr in tracks:
                raw_b = tr["name"].lower()
                clean_b = re.sub(r'_(?:se|nose)$', '', raw_b)
                if clean_b not in seen_bases:
                    seen_bases[clean_b] = tr
                    filtered.append(tr)
                elif tr["title"].lower().endswith(".mp3") and seen_bases[clean_b]["title"].lower().endswith(".wav"):
                    filtered.remove(seen_bases[clean_b])
                    seen_bases[clean_b] = tr
                    filtered.append(tr)

            filtered.sort(key=lambda x: _natural_sort_key(x["title"]))
            return filtered

    # Final fallback if no preferred folders matched
    all_audios = []
    for item in tree:
        all_audios.extend(extract_audios_from_node(item))
    unique_audios = []
    seen = set()
    for a in all_audios:
        b = a["name"].lower()
        if b not in seen:
            seen.add(b)
            unique_audios.append(a)
    unique_audios.sort(key=lambda x: _natural_sort_key(x["title"]))
    return unique_audios


def discover_all_audio_tracks(rj_id, referer="https://japaneseasmr.com", user_agent="Mozilla/5.0"):
    """
    Discover all audio tracks (Track 1..N, Omake, Bonus) for a specified RJ code:
    1. Check primary source: JapaneseASMR (.m3u8 master playlist or multi-track MP3 files).
    2. Automatically fallback to asmr.one API via smart track filtering if primary source is absent.
    """
    import re
    clean_id = rj_id.strip()
    if clean_id.startswith("http://") or clean_id.startswith("https://"):
        return [{"name": "Track 1", "url": clean_id, "referer": referer, "source": "direct"}]

    # 1. Check for master HLS .m3u8 playlist on JapaneseASMR
    m3u8_url = f"https://v.weeab0o.xyz/{clean_id}.m3u8"
    if check_url_exists(m3u8_url, referer, user_agent):
        return [{"name": "Track 1", "url": m3u8_url, "referer": referer, "source": "japaneseasmr"}]

    found_tracks = []

    # 2. Check Track 1 (.mp3) on JapaneseASMR
    t1_candidates = [
        f"https://v.weeab0o.xyz/{clean_id}.mp3",
        f"https://v.weeab0o.xyz/{clean_id}%201.mp3",
        f"https://v.weeab0o.xyz/{clean_id}_1.mp3",
        f"https://v.weeab0o.xyz/{clean_id}-1.mp3",
    ]
    t1_url = None
    for url in t1_candidates:
        if check_url_exists(url, referer, user_agent):
            t1_url = url
            break

    if t1_url:
        found_tracks.append({"name": "Track 1", "url": t1_url, "referer": referer, "source": "japaneseasmr"})

        # 3. Check Tracks 2 through 20 (.mp3)
        for track_num in range(2, 21):
            num_candidates = [
                f"https://v.weeab0o.xyz/{clean_id}%20{track_num}.mp3",
                f"https://v.weeab0o.xyz/{clean_id}_{track_num}.mp3",
                f"https://v.weeab0o.xyz/{clean_id}-{track_num}.mp3",
                f"https://v.weeab0o.xyz/{clean_id}{track_num}.mp3",
            ]
            matched_url = None
            for url in num_candidates:
                if check_url_exists(url, referer, user_agent):
                    matched_url = url
                    break
            if matched_url:
                found_tracks.append({"name": f"Track {track_num}", "url": matched_url, "referer": referer, "source": "japaneseasmr"})
            else:
                if track_num >= 4:
                    break

        # 4. Check Omake, Bonus, Tokuten, and EX tracks (.mp3)
        omake_patterns = [
            ("Omake", f"https://v.weeab0o.xyz/{clean_id}omake.mp3"),
            ("Omake", f"https://v.weeab0o.xyz/{clean_id}%20omake.mp3"),
            ("Omake", f"https://v.weeab0o.xyz/{clean_id}_omake.mp3"),
            ("Omake", f"https://v.weeab0o.xyz/{clean_id}-omake.mp3"),
            ("Omake 1", f"https://v.weeab0o.xyz/{clean_id}omake1.mp3"),
            ("Omake 1", f"https://v.weeab0o.xyz/{clean_id}%20omake%201.mp3"),
            ("Omake 2", f"https://v.weeab0o.xyz/{clean_id}omake2.mp3"),
            ("Omake 2", f"https://v.weeab0o.xyz/{clean_id}%20omake%202.mp3"),
            ("Bonus", f"https://v.weeab0o.xyz/{clean_id}bonus.mp3"),
            ("Bonus", f"https://v.weeab0o.xyz/{clean_id}%20bonus.mp3"),
            ("Bonus", f"https://v.weeab0o.xyz/{clean_id}_bonus.mp3"),
            ("Tokuten", f"https://v.weeab0o.xyz/{clean_id}tokuten.mp3"),
            ("Tokuten", f"https://v.weeab0o.xyz/{clean_id}%20tokuten.mp3"),
            ("EX", f"https://v.weeab0o.xyz/{clean_id}%20ex.mp3"),
            ("EX", f"https://v.weeab0o.xyz/{clean_id}ex.mp3"),
            ("EX", f"https://v.weeab0o.xyz/{clean_id}_ex.mp3"),
            ("EX", f"https://v.weeab0o.xyz/{clean_id}-ex.mp3"),
            ("EX 1", f"https://v.weeab0o.xyz/{clean_id}%20ex%201.mp3"),
            ("EX 1", f"https://v.weeab0o.xyz/{clean_id}%20ex1.mp3"),
            ("EX 2", f"https://v.weeab0o.xyz/{clean_id}%20ex%202.mp3"),
            ("EX 2", f"https://v.weeab0o.xyz/{clean_id}%20ex2.mp3"),
        ]
        seen_urls = {t["url"] for t in found_tracks}
        for om_name, om_url in omake_patterns:
            if om_url not in seen_urls and check_url_exists(om_url, referer, user_agent):
                found_tracks.append({"name": om_name, "url": om_url, "referer": referer, "source": "japaneseasmr"})
                seen_urls.add(om_url)

        return found_tracks

    # 5. Fallback to asmr.one if JapaneseASMR primary source is absent
    num_id = re.sub(r'^[A-Za-z]+', '', clean_id)
    if num_id:
        asmrone_tree = fetch_asmrone_tree(num_id)
        if asmrone_tree:
            asmr_tracks = filter_smart_asmrone_tracks(asmrone_tree)
            if asmr_tracks:
                return asmr_tracks

    # Final single-track fallback
    return [{"name": "Track 1", "url": t1_candidates[0], "referer": referer, "source": "japaneseasmr"}]


def resolve_audio_url(rj_id, referer="https://japaneseasmr.com", user_agent="Mozilla/5.0"):
    """Resolve the URL for the first audio track of a work."""
    tracks = discover_all_audio_tracks(rj_id, referer, user_agent)
    return tracks[0]["url"] if tracks else f"https://v.weeab0o.xyz/{rj_id}.mp3"


def get_precise_duration_seconds(file_path):
    """Extract exact audio duration in seconds via ffprobe or ffmpeg fallback."""
    if not os.path.isfile(file_path):
        return 0.0
    import re
    ffprobe_bin = get_bin_executable("ffprobe")
    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            timeout=12,
        )
        val = float(res.stdout.strip())
        if val > 0:
            return val
    except Exception:
        pass

    # Fallback to ffmpeg -i
    try:
        ffmpeg_bin = get_bin_executable("ffmpeg")
        cmd = [ffmpeg_bin, "-hide_banner", "-i", file_path]
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            timeout=12,
        )
        txt = res.stderr.decode("utf-8", errors="ignore")
        m = re.search(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)', txt)
        if m:
            h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
            return h * 3600 + mi * 60 + s
    except Exception:
        pass
    return 0.0


def get_audio_codec(file_path):
    """Identify primary audio stream codec (e.g., 'aac', 'mp3', 'flac') via ffprobe."""
    if not os.path.isfile(file_path):
        return ""
    ffprobe_bin = get_bin_executable("ffprobe")
    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-select_streams", "a:0",
        "-show_entries", "stream=codec_name",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path,
    ]
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            timeout=10,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip().lower()
    except Exception:
        pass
    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".m4a", ".aac"):
        return "aac"
    elif ext == ".mp3":
        return "mp3"
    elif ext == ".flac":
        return "flac"
    elif ext == ".wav":
        return "pcm"
    return ""


def resolve_japaneseasmr_url_to_rjid(url):
    """Extract canonical RJ-ID from a japaneseasmr.com post URL."""
    import urllib.request
    import re
    if not url or "japaneseasmr.com" not in str(url).lower():
        return None
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        req = urllib.request.Request(str(url).strip(), headers=headers)
        with urllib.request.urlopen(req, timeout=6) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        m = re.search(r'https?://v\.weeab0o\.xyz/(RJ\d+)', html, re.I)
        if m:
            return m.group(1).upper()
        m2 = re.search(r'product_id/(RJ\d+)', html, re.I)
        if m2:
            return m2.group(1).upper()
        m3 = re.search(r'\b(RJ\d{6,8})\b', html, re.I)
        if m3:
            return m3.group(1).upper()
    except Exception:
        pass
    return None


def resolve_input_to_rjid(input_str):
    """
    Normalize raw user input (RJ-ID, asmr.one URL, japaneseasmr.com URL, or dlsite.com URL)
    to canonical RJ format (e.g., 'RJ01220411').
    """
    import re
    if not input_str:
        return None
    token = str(input_str).strip()
    if not token:
        return None

    # 1. asmr.one link (e.g., https://asmr.one/work/RJ01220411 or /work/01220411)
    if "asmr.one" in token.lower():
        m = re.search(r'asmr\.one/(?:work|api/work)/([A-Za-z0-9]+)', token, re.I)
        if m:
            val = m.group(1).upper()
            if not val.startswith("RJ"):
                val = f"RJ{val}"
            return val

    # 2. japaneseasmr.com link (e.g., https://japaneseasmr.com/151339/)
    if "japaneseasmr.com" in token.lower():
        rj = resolve_japaneseasmr_url_to_rjid(token)
        if rj:
            return rj

    # 3. DLsite link (e.g., https://www.dlsite.com/maniax/work/=/product_id/RJ01220411.html)
    if "dlsite.com" in token.lower():
        m = re.search(r'product_id/(RJ\d+)', token, re.I)
        if m:
            return m.group(1).upper()

    # 4. Direct RJ code or pure numeric identifier
    m = re.search(r'(RJ\d+|\b\d{5,8}\b)', token, re.I)
    if m:
        val = m.group(1).upper()
        if not val.startswith("RJ"):
            val = f"RJ{val}"
        return val

    clean_val = token.upper()
    if re.match(r'^\d+$', clean_val):
        return f"RJ{clean_val}"
    return clean_val


def fetch_japaneseasmr_chapters(rj_id_or_url, meta=None):
    """
    Fetch tracklist and chapter timestamps directly from japaneseasmr.com post content:
    - If input is a post URL (e.g., https://japaneseasmr.com/150854/), fetch directly.
    - If input is an RJ code (e.g., RJ01691063), query japaneseasmr.com/?s={rj_id} to locate the post.
    - Supports optional meta dictionary to accelerate lookup if post URL is already known.
    - Extracts start time (milliseconds) and titles from .chapter_list table or entry text.

    Returns:
        list of dict: [{"start": ms, "title": "..."}]
    """
    import urllib.request
    from bs4 import BeautifulSoup
    import re

    clean_target = str(rj_id_or_url).strip()
    if not clean_target:
        return []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Referer": "https://japaneseasmr.com/",
    }

    target_url = None
    if isinstance(meta, dict):
        cand_url = meta.get("japaneseasmr_url") or meta.get("post_url") or meta.get("url") or ""
        if cand_url.startswith("http://") or cand_url.startswith("https://"):
            target_url = cand_url

    if not target_url:
        if clean_target.startswith("http://") or clean_target.startswith("https://"):
            target_url = clean_target
        else:
            clean_id = clean_target.upper()
            search_url = f"https://japaneseasmr.com/?s={clean_id}"
            try:
                req = urllib.request.Request(search_url, headers=headers)
                with urllib.request.urlopen(req, timeout=8) as resp:
                    s_html = resp.read().decode("utf-8", errors="replace")
                soup_s = BeautifulSoup(s_html, "html.parser")
                entries = soup_s.find_all(class_=re.compile(r"entry-title|post-title"))
                for ent in entries:
                    a_tag = ent.find("a")
                    if a_tag and a_tag.get("href"):
                        if clean_id in ent.get_text().upper() or not target_url:
                            target_url = a_tag["href"]
                            if clean_id in ent.get_text().upper():
                                break
                if not target_url:
                    posts = re.findall(r"https://japaneseasmr\.com/\d+/", s_html)
                    if posts:
                        target_url = posts[0]
            except Exception:
                return []

    if not target_url:
        return []

    try:
        req = urllib.request.Request(target_url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            p_html = resp.read().decode("utf-8", errors="replace")
    except Exception:
        return []

    def _parse_ts(ts):
        parts = ts.strip().split(":")
        try:
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
        except Exception:
            pass
        return None

    soup = BeautifulSoup(p_html, "html.parser")
    raw_chapters = []
    seen = set()

    for tr in soup.find_all("tr"):
        time_td = tr.find("td", class_=lambda c: c and "start_time" in c)
        title_td = tr.find("td", class_=lambda c: c and "chapter_title" in c)
        if time_td and title_td:
            sec_val = None
            link = time_td.find("a")
            if link and link.get("data-value"):
                try:
                    sec_val = float(link.get("data-value"))
                except (ValueError, TypeError):
                    pass
            time_text = time_td.get_text(strip=True)
            if sec_val is None and time_text:
                sec_val = _parse_ts(time_text)

            title_text = ""
            tlink = title_td.find("a")
            if tlink and tlink.get("data-track-title"):
                title_text = tlink.get("data-track-title").strip()
            if not title_text:
                title_text = title_td.get_text(strip=True)

            if sec_val is not None and title_text:
                key = (sec_val, title_text)
                if key not in seen:
                    seen.add(key)
                    raw_chapters.append((sec_val, title_text))

    # Text fallback if no structured chapter table exists
    if not raw_chapters:
        entry_content = soup.find(class_=re.compile(r"entry-content|post-content"))
        if entry_content:
            text = entry_content.get_text()
            # Pattern 1: Leading line timestamps (e.g., "00:00:00 Track 1")
            for m in re.finditer(r"(?:^|\n)\s*(\d{1,2}:\d{2}(?::\d{2})?)\s+([^\n\r<]+)", text):
                sec = _parse_ts(m.group(1))
                t_str = m.group(2).strip()
                if sec is not None and t_str and len(t_str) < 120:
                    key = (sec, t_str)
                    if key not in seen:
                        seen.add(key)
                        raw_chapters.append((sec, t_str))

            # Pattern 2: Title followed by duration (e.g., "00 introduction 2:38", "01 ... 5:26")
            if not raw_chapters:
                dur_matches = re.findall(r"(?:^|\s)(\d{1,2}\s+[^\s\d][^\n\r\t]{1,60}?)\s+(\d{1,2}:\d{2})(?=\s|$)", text)
                if len(dur_matches) >= 2:
                    seen_titles = set()
                    curr_sec = 0.0
                    for t_name, dur_s in dur_matches:
                        clean_t = t_name.strip()
                        if clean_t in seen_titles:
                            break
                        seen_titles.add(clean_t)
                        d_sec = _parse_ts(dur_s)
                        if d_sec and d_sec > 0:
                            raw_chapters.append((curr_sec, clean_t))
                            curr_sec += d_sec

    raw_chapters.sort(key=lambda x: x[0])
    result = []
    for sec, title in raw_chapters:
        clean_name = re.sub(r"\.(?:mp3|wav|m4a|flac|aac|ogg)$", "", title, flags=re.I).strip()
        result.append({
            "start": int(sec * 1000),
            "title": clean_name or "Track",
        })
    return result


def generate_chapter_metadata(track_files, track_names=None, rj_id=None, temp_dir=None, log_func=print):
    """
    Generate an FFMPEG chapter metadata file (FFMETADATA1) using smart hybrid chapter mapping:
    - Case A (JapaneseASMR Master + Omake):
      If the duration of track_files[0] matches the total chapter duration from asmr.one (+- 2.5s),
      split track_files[0] into narrative chapters, appending track_files[1:] (omake/bonus) as subsequent chapters.
    - Case B (Multi-track 1-to-1):
      If physical track count matches asmr.one track count and total duration aligns (+- 2.5s),
      synchronize chapter names with titles from asmr.one.
    - Case B2 (JapaneseASMR Embedded Tracklist):
      If asmr.one has no entry, extract chapter markers and timestamps directly from japaneseasmr.com.
    - Case C (Pure Physical Multi-track):
      If multiple files exist without external chapter matches, generate chapters from individual physical tracks.

    Returns:
        tuple: (path to ffmetadata.txt, chapter_count, list_of_chapters) if valid, else (None, 0, []).
    """
    import re
    if not temp_dir:
        temp_dir = os.path.dirname(track_files[0]) if track_files else os.path.join(".cache", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    meta_path = os.path.join(temp_dir, f"chapters_{rj_id or 'audio'}_{int(time.time()*1000)}.txt")

    chapters = []
    hybrid_matched = False

    if rj_id and track_files:
        num_id = re.sub(r'^[A-Za-z]+', '', rj_id.strip())
        if num_id:
            try:
                tree = fetch_asmrone_tree(num_id)
                if tree:
                    cand_tracks = filter_smart_asmrone_tracks(tree)
                    if cand_tracks and len(cand_tracks) > 1:
                        sum_asmr_sec = sum(float(t.get("duration") or 0.0) for t in cand_tracks)
                        t0_dur = get_precise_duration_seconds(track_files[0])

                        # Case A: Track 1 is a master compilation matching total asmr.one chapter duration (+- 2.5s)
                        if t0_dur > 10 and abs(t0_dur - sum_asmr_sec) <= 2.5:
                            curr_ms = 0
                            for t in cand_tracks:
                                dur_ms = int(float(t.get("duration") or 0.0) * 1000)
                                raw_name = t.get("name") or t.get("title") or "Track"
                                clean_name = re.sub(r'\.(?:mp3|wav|m4a|flac|aac|ogg)$', '', raw_name, flags=re.I).strip()
                                clean_name = re.sub(r'_(?:SE|NoSE)$', '', clean_name, flags=re.I).strip()
                                chapters.append({
                                    "start": curr_ms,
                                    "end": curr_ms + dur_ms,
                                    "title": clean_name or "Track"
                                })
                                curr_ms += dur_ms

                            # Append additional physical files on disk (e.g. Omake, Bonus, EX in track_files[1:])
                            if len(track_files) > 1:
                                for idx, tf in enumerate(track_files[1:], start=1):
                                    dur_sec = get_precise_duration_seconds(tf)
                                    dur_ms = int(dur_sec * 1000)
                                    t_title = track_names[idx] if (track_names and idx < len(track_names)) else f"Omake {idx}"
                                    clean_title = re.sub(r'\.(?:mp3|wav|m4a|flac|aac|ogg)$', '', t_title, flags=re.I).strip()
                                    chapters.append({
                                        "start": curr_ms,
                                        "end": curr_ms + dur_ms,
                                        "title": clean_title or f"Omake {idx}"
                                    })
                                    curr_ms += dur_ms

                            hybrid_matched = True
                            if log_func:
                                omake_count = len(track_files) - 1
                                extra_str = f" + {omake_count} omake" if omake_count > 0 else ""
                                log_func(f"[✓] Hybrid Chapter: Track utama ({t0_dur:.1f}s) berhasil dipetakan menjadi {len(cand_tracks)} bab cerita{extra_str}!")

                        # Case B: Total duration of all physical files matches asmr.one and track counts align
                        elif len(track_files) == len(cand_tracks):
                            tot_phys_sec = sum(get_precise_duration_seconds(tf) for tf in track_files)
                            if abs(tot_phys_sec - sum_asmr_sec) <= 2.5:
                                curr_ms = 0
                                for idx, tf in enumerate(track_files):
                                    dur_sec = get_precise_duration_seconds(tf)
                                    dur_ms = int(dur_sec * 1000)
                                    cand_name = cand_tracks[idx].get("name") or cand_tracks[idx].get("title")
                                    t_title = cand_name or (track_names[idx] if track_names and idx < len(track_names) else f"Track {idx+1}")
                                    clean_title = re.sub(r'\.(?:mp3|wav|m4a|flac|aac|ogg)$', '', t_title, flags=re.I).strip()
                                    clean_title = re.sub(r'_(?:SE|NoSE)$', '', clean_title, flags=re.I).strip()
                                    chapters.append({
                                        "start": curr_ms,
                                        "end": curr_ms + dur_ms,
                                        "title": clean_title or f"Track {idx+1}"
                                    })
                                    curr_ms += dur_ms
                                hybrid_matched = True
                                if log_func:
                                    log_func(f"[✓] Terverifikasi: {len(chapters)} track fisik disinkronkan dengan metadata asmr.one!")
            except Exception:
                pass

    # Case B2: If asmr.one has no chapter listing, query and extract directly from japaneseasmr.com
    if not hybrid_matched and rj_id and track_files:
        try:
            j_chaps = fetch_japaneseasmr_chapters(rj_id)
            if j_chaps and len(j_chaps) > 1:
                t0_dur = get_precise_duration_seconds(track_files[0])
                for i, ch in enumerate(j_chaps):
                    s_ms = ch["start"]
                    if i + 1 < len(j_chaps):
                        e_ms = j_chaps[i + 1]["start"]
                    else:
                        e_ms = int(t0_dur * 1000) if t0_dur > 0 else (s_ms + 60000)
                    chapters.append({
                        "start": s_ms,
                        "end": max(s_ms + 1000, e_ms),
                        "title": ch["title"],
                    })

                # Append additional physical files on disk (e.g. Omake, Bonus, EX in track_files[1:])
                if len(track_files) > 1:
                    last_end = chapters[-1]["end"]
                    for idx, tf in enumerate(track_files[1:], start=1):
                        dur_sec = get_precise_duration_seconds(tf)
                        dur_ms = int(dur_sec * 1000)
                        t_title = track_names[idx] if (track_names and idx < len(track_names)) else f"Omake {idx}"
                        clean_title = re.sub(r'\.(?:mp3|wav|m4a|flac|aac|ogg)$', '', t_title, flags=re.I).strip()
                        chapters.append({
                            "start": last_end,
                            "end": last_end + dur_ms,
                            "title": clean_title or f"Omake {idx}"
                        })
                        last_end += dur_ms

                hybrid_matched = True
                if log_func:
                    log_func(f"[✓] Tracklist JapaneseASMR: Berhasil menyinkronkan {len(chapters)} bab cerita dari situs japaneseasmr.com!")
        except Exception:
            pass

    # Case C: Pure physical multi-track fallback
    if not hybrid_matched and len(track_files) > 1:
        curr_ms = 0
        for idx, tf in enumerate(track_files):
            dur_sec = get_precise_duration_seconds(tf)
            dur_ms = int(dur_sec * 1000)
            t_title = track_names[idx] if (track_names and idx < len(track_names)) else f"Track {idx + 1}"
            clean_title = re.sub(r'\.(?:mp3|wav|m4a|flac|aac|ogg)$', '', t_title, flags=re.I).strip()
            chapters.append({
                "start": curr_ms,
                "end": curr_ms + dur_ms,
                "title": clean_title or f"Track {idx + 1}"
            })
            curr_ms += dur_ms

    if chapters and len(chapters) > 1:
        try:
            with open(meta_path, "w", encoding="utf-8") as f:
                f.write(";FFMETADATA1\n")
                for ch in chapters:
                    f.write("[CHAPTER]\n")
                    f.write("TIMEBASE=1/1000\n")
                    f.write(f"START={ch['start']}\n")
                    f.write(f"END={ch['end']}\n")
                    safe_title = ch['title'].replace("=", "\\=").replace(";", "\\;").replace("#", "\\#")
                    f.write(f"title={safe_title}\n")
            return meta_path, len(chapters), chapters
        except Exception:
            pass

    return None, 0, []


def write_cue_sheet(output_audio_path, chapters, meta=None):
    """
    Generate a companion CUE sheet (.cue) for MP3 or M4A audio files,
    allowing standalone audio players (Foobar2000, AIMP, MusicBee, VLC)
    to parse and split chapters instantaneously.
    """
    if not chapters or len(chapters) <= 1:
        return None
    cue_path = os.path.splitext(output_audio_path)[0] + ".cue"
    audio_fname = os.path.basename(output_audio_path)
    meta = meta or {}
    artist = meta.get("cv") if meta.get("cv") and meta.get("cv") != "-" else "JapaneseASMR"
    album = meta.get("title") or os.path.splitext(audio_fname)[0]
    safe_artist = artist.replace('"', "'")
    safe_album = album.replace('"', "'")
    safe_audio_fname = audio_fname.replace('"', "'")
    file_type = "MP4" if output_audio_path.lower().endswith(".m4a") else "MP3"

    lines = [
        f'PERFORMER "{safe_artist}"',
        f'TITLE "{safe_album}"',
        f'FILE "{safe_audio_fname}" {file_type}',
    ]
    for idx, ch in enumerate(chapters):
        t_num = idx + 1
        t_title = ch.get("title") or f"Track {t_num}"
        safe_title = t_title.replace('"', "'")
        ms = ch.get("start") if "start" in ch else ch.get("start_ms", 0)
        tot_sec = ms / 1000.0
        mm = int(tot_sec // 60)
        ss = int(tot_sec % 60)
        ff = int((tot_sec - int(tot_sec)) * 75)
        lines.append(f"  TRACK {t_num:02d} AUDIO")
        lines.append(f'    TITLE "{safe_title}"')
        lines.append(f"    INDEX 01 {mm:02d}:{ss:02d}:{ff:02d}")

    try:
        with open(cue_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        return cue_path
    except Exception:
        return None


def parse_cue_file(cue_path):
    """
    Parse a .cue sheet file into a structured chapter list.

    Returns:
        list of dict: [{'index': 1, 'title': '...', 'start_ms': 0}, ...]
    """
    if not os.path.exists(cue_path):
        return []
    chapters = []
    curr = {}
    content = None
    for enc in ("utf-8-sig", "utf-8", "cp932", "shift_jis"):
        try:
            with open(cue_path, "r", encoding=enc) as f:
                content = f.read()
                break
        except (UnicodeDecodeError, Exception):
            continue

    if not content:
        try:
            with open(cue_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            return []

    try:
        for line in content.splitlines():
            line = line.strip()
            m_tr = re.match(r"^TRACK\s+(\d+)\s+AUDIO", line, re.I)
            if m_tr:
                if curr:
                    chapters.append(curr)
                curr = {"index": int(m_tr.group(1)), "title": f"Track {m_tr.group(1)}", "start_ms": 0}
            m_ti = re.match(r'^TITLE\s+"?(.*?)"?$', line, re.I)
            if m_ti and curr:
                curr["title"] = m_ti.group(1).strip('"')
            m_idx = re.match(r"^INDEX\s+01\s+(\d+):(\d+):(\d+)", line, re.I)
            if m_idx and curr:
                mm, ss, ff = int(m_idx.group(1)), int(m_idx.group(2)), int(m_idx.group(3))
                curr["start_ms"] = (mm * 60 + ss) * 1000 + int((ff / 75.0) * 1000)
        if curr:
            chapters.append(curr)
    except Exception:
        pass
    return chapters


def extract_chapters_from_audio(file_path):
    """
    Extract chapter marks from an audio file:
    1. Parse companion .cue sheet if available on disk.
    2. Fallback to extracting embedded chapter atom tags via ffprobe.
    """
    if not file_path or not os.path.exists(file_path):
        return []

    norm_file = os.path.abspath(file_path)

    # 1. Check companion CUE sheet first
    cue_path = os.path.splitext(norm_file)[0] + ".cue"
    if os.path.exists(cue_path):
        cue_chapters = parse_cue_file(cue_path)
        if len(cue_chapters) >= 1:
            return cue_chapters

    # 2. Query embedded chapters via ffprobe
    ffprobe = get_bin_executable("ffprobe")
    try:
        res = subprocess.run(
            [ffprobe, "-hide_banner", "-loglevel", "error", "-i", norm_file, "-show_chapters"],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        out = res.stdout.decode("utf-8", errors="replace")
        chapters = []
        curr = {}
        for line in out.splitlines():
            line = line.strip()
            if line == "[CHAPTER]":
                curr = {"index": len(chapters) + 1, "title": f"Bab {len(chapters) + 1}", "start_ms": 0}
            elif line == "[/CHAPTER]":
                if curr and "start_ms" in curr:
                    chapters.append(curr)
                curr = {}
            elif line.lower().startswith("start_time="):
                try:
                    curr["start_ms"] = int(float(line.split("=", 1)[1]) * 1000)
                except Exception:
                    pass
            elif line.lower().startswith("tag:title="):
                curr["title"] = line.split("=", 1)[1].strip()
        if curr and "start_ms" in curr:
            chapters.append(curr)
        return chapters
    except Exception:
        return []


def embed_cover_and_merge(track_files, cover_path, output_name, track_names=None, meta=None, rj_id=None, log_func=print):
    """
    Merge multi-track audio (if applicable), embed high-resolution cover art,
    complete metadata tags, and insert chapter markers into the output container.
    Supports .m4a (with QuickTime chapter track) and .mp3 container targets.
    """
    ffmpeg_bin = get_bin_executable("ffmpeg")
    meta = meta or {}
    clean_rj = rj_id or meta.get("rjid", "")
    title_val = meta.get("title") or os.path.splitext(os.path.basename(output_name))[0]
    artist_val = meta.get("cv") if meta.get("cv") and meta.get("cv") != "-" else "JapaneseASMR"
    album_val = meta.get("circle") if meta.get("circle") and meta.get("circle") != "-" else (clean_rj or "JapaneseASMR")
    genre_val = meta.get("genre") if meta.get("genre") and meta.get("genre") != "-" else "ASMR"
    rating_val = meta.get("age_rating") or "-"

    is_m4a = output_name.lower().endswith(".m4a")
    temp_dir = os.path.dirname(track_files[0]) if track_files else os.path.join(".cache", "temp")
    os.makedirs(temp_dir, exist_ok=True)
    cleanup_list = []

    # 1. Generate chapter metadata if applicable
    meta_chapter_file, num_chaps, parsed_chapters = generate_chapter_metadata(
        track_files, track_names=track_names, rj_id=clean_rj, temp_dir=temp_dir, log_func=log_func
    )
    if meta_chapter_file:
        cleanup_list.append(meta_chapter_file)
        if log_func:
            log_func(f"[i] Menyematkan {num_chaps} penanda bab (chapters) ke dalam {os.path.basename(output_name)}...")

    # 2. Prepare audio inputs (concat demuxer list for multi-track, or direct file)
    if len(track_files) > 1:
        concat_list_file = os.path.join(temp_dir, f"concat_{clean_rj or 'merge'}_{int(time.time()*1000)}.txt")
        cleanup_list.append(concat_list_file)
        with open(concat_list_file, "w", encoding="utf-8") as f_concat:
            for tf in track_files:
                safe_p = os.path.abspath(tf).replace("\\", "/")
                f_concat.write(f"file '{safe_p}'\n")
        audio_input_args = ["-f", "concat", "-safe", "0", "-i", concat_list_file]
        comment_val = f"Rating: {rating_val} | Tracks: {len(track_files)} Gabungan ({', '.join(track_names or [])})"
    else:
        audio_input_args = ["-i", track_files[0]]
        comment_val = f"Rating: {rating_val} | Circle: {album_val} | CV: {artist_val}"

    # 3. Assemble baseline FFmpeg CLI parameters
    base_cmd = [ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-y", "-threads", "0"]
    base_cmd.extend(audio_input_args)

    input_count = 1
    chapter_input_idx = -1
    if meta_chapter_file:
        base_cmd.extend(["-f", "ffmetadata", "-i", meta_chapter_file])
        chapter_input_idx = input_count
        input_count += 1

    cover_input_idx = -1
    if cover_path and os.path.isfile(cover_path):
        base_cmd.extend(["-i", cover_path])
        cover_input_idx = input_count
        input_count += 1

    # Mapping streams
    base_cmd.extend(["-map", "0:a"])
    if cover_input_idx != -1:
        base_cmd.extend(["-map", f"{cover_input_idx}:v", "-c:v", "mjpeg", "-disposition:v:0", "attached_pic"])

    if chapter_input_idx != -1:
        base_cmd.extend(["-map_metadata", str(chapter_input_idx), "-map_chapters", str(chapter_input_idx)])

    # Metadata tags
    meta_tags = []
    if cover_input_idx != -1:
        meta_tags.extend(["-metadata:s:v", "title=Album cover", "-metadata:s:v", "comment=Cover (front)"])

    meta_tags.extend([
        "-metadata", f"title={title_val}",
        "-metadata", f"artist={artist_val}",
        "-metadata", f"album={album_val}",
        "-metadata", f"genre={genre_val}",
        "-metadata", f"comment={comment_val}",
    ])

    # Inspect input codec for fast remuxing (prevents unnecessary CPU transcoding)
    input_codecs = [get_audio_codec(tf) for tf in track_files if os.path.exists(tf)]
    all_same_codec = len(set(input_codecs)) == 1 if input_codecs else False
    primary_codec = input_codecs[0] if input_codecs else ""

    can_fast_remux = False
    if is_m4a and all_same_codec and primary_codec == "aac":
        can_fast_remux = True
    elif (not is_m4a) and all_same_codec and primary_codec == "mp3":
        can_fast_remux = True

    if is_m4a:
        remux_args = ["-c:a", "copy", "-movflags", "+faststart", "-f", "ipod"]
        reencode_args = ["-c:a", "aac_mf", "-b:a", "256k", "-movflags", "+faststart", "-f", "ipod"]
        reencode_fallback = ["-c:a", "aac", "-aac_coder", "fast", "-b:a", "256k", "-threads", "0", "-movflags", "+faststart", "-f", "ipod"]
    else:
        remux_args = ["-c:a", "copy", "-id3v2_version", "3"]
        reencode_args = ["-c:a", "libmp3lame", "-b:a", "320k", "-threads", "0", "-id3v2_version", "3"]
        reencode_fallback = ["-c:a", "libmp3lame", "-b:a", "320k", "-id3v2_version", "3"]

    def _exec_ffmpeg(codec_args):
        full_cmd = list(base_cmd) + list(codec_args) + list(meta_tags) + [output_name]
        subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            check=True,
        )

    try:
        if can_fast_remux:
            if log_func:
                log_func("[+] Mengemas audio sesuai format asli (Fast Remux instan)...")
            try:
                _exec_ffmpeg(remux_args)
            except subprocess.CalledProcessError as remux_err:
                if log_func:
                    log_func("[!] Menyesuaikan format audio...")
                try:
                    _exec_ffmpeg(reencode_args)
                except subprocess.CalledProcessError:
                    _exec_ffmpeg(reencode_fallback)
        else:
            if log_func:
                target_str = "M4A" if is_m4a else "MP3"
                log_func(f"[i] Memproses format audio ({target_str})...")
            try:
                _exec_ffmpeg(reencode_args)
            except subprocess.CalledProcessError:
                _exec_ffmpeg(reencode_fallback)

        # Generate companion CUE sheet for MP3 containers so standalone audio players parse chapters
        if not is_m4a and parsed_chapters:
            cue_res = write_cue_sheet(output_name, parsed_chapters, meta=meta)
            if cue_res and log_func:
                log_func(f"[✓] CUE Sheet dibuat untuk pemutar audio (Foobar2000): {os.path.basename(cue_res)}")
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.strip() if e.stderr else str(e)
        raise RuntimeError(f"FFmpeg muxing gagal: {err_msg}")
    finally:
        for cl_file in cleanup_list:
            if os.path.exists(cl_file):
                try:
                    os.remove(cl_file)
                except OSError:
                    pass

