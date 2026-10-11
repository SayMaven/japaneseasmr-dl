import json
import os
import shutil
import subprocess
import sys
import time
from PIL import Image

# Daftarkan folder bin/ ke PATH environment agar binary (yt-dlp, ffmpeg, aria2c) selalu ditemukan
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
    """Mencari path absolut executable (yt-dlp, ffmpeg, aria2c) agar selalu ditemukan di komputer baru."""
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

    # Fallback ke system PATH
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
    "auto_clipboard": False,
    "ytdlp_channel": "stable",
    "audio_format": "auto",
}


def get_ytdlp_version():
    """Mengambil versi yt-dlp yang terpasang."""
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
        return "Tidak diketahui"
    except Exception:
        return "Tidak ditemukan"


def update_ytdlp_engine(channel="stable"):
    """
    Memperbarui binary yt-dlp ke rilis stable atau nightly (@latest).
    Mengembalikan: (success: bool, status_code: str, display_message: str)
    status_code: 'already_latest' | 'updated' | 'error'
    """
    import subprocess
    target_channel = channel.strip().lower()
    if target_channel not in ["stable", "nightly"]:
        target_channel = "stable"

    ytdlp_bin = get_bin_executable("yt-dlp")
    # Gunakan @latest agar yt-dlp bersedia beralih/downgrade antar-saluran (misal dari nightly ke stable)
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
    """Menghitung total ukuran file di dalam folder dalam format MB/KB."""
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
    """Mengembalikan statistik ukuran cache cover dan cache temp."""
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
    """Menghapus semua file thumbnail cover di .cache/covers/."""
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
    """Menghapus semua file sementara/part di .cache/temp/."""
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
    """Mengosongkan history.json."""
    save_history([])


def load_config():
    """Memuat konfigurasi dari config.json."""
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            # Pastikan semua key default ada
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
            return cfg
    except Exception:
        return dict(DEFAULT_CONFIG)


def save_config(config_dict):
    """Menyimpan konfigurasi ke config.json."""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] Gagal menyimpan config.json: {e}")


def get_download_dir():
    """Mengambil path folder download dari config."""
    cfg = load_config()
    d_dir = cfg.get("download_dir", "downloads")
    os.makedirs(d_dir, exist_ok=True)
    return d_dir


def set_download_dir(new_dir):
    """Memperbarui folder download dan menyimpannya ke config.json."""
    if not new_dir:
        return
    cfg = load_config()
    cfg["download_dir"] = new_dir
    save_config(cfg)
    os.makedirs(new_dir, exist_ok=True)


def get_audio_format():
    """Mengambil format audio output dari config ('auto', 'm4a', atau 'mp3'). Default: 'auto'."""
    cfg = load_config()
    fmt = str(cfg.get("audio_format", "auto")).strip().lower()
    if fmt in ("auto", "smart", "default"):
        return "auto"
    return "m4a" if fmt in ("m4a", "aac") else "mp3"


def set_audio_format(fmt):
    """Menyimpan pilihan format audio ('auto', 'm4a', 'mp3') ke config.json."""
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


def load_history():
    """Memuat daftar riwayat unduhan dari history.json."""
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(history_list):
    """Menyimpan daftar riwayat unduhan ke history.json."""
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history_list, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] Gagal menyimpan history.json: {e}")


def cache_cover_image(rjid, source_cover_path):
    """Menyimpan thumbnail cover kecil ke .cache/covers/RJxxxxxx.jpg."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"{rjid}.jpg")
    try:
        with Image.open(source_cover_path) as img:
            img.thumbnail((320, 240))
            img.convert("RGB").save(cache_path, "JPEG", quality=85)
        return cache_path
    except Exception:
        # Fallback copy biasa jika gagal resize
        try:
            shutil.copy2(source_cover_path, cache_path)
            return cache_path
        except Exception:
            return None


def add_to_history(rjid, title, cv, circle, cover_url, output_path, temp_cover_path=None, genre="-", age_rating="-"):
    """Menambahkan rekaman unduhan baru ke history.json dan membuat cache cover."""
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
    """Mengecek apakah URL dapat diakses (200 / 206 OK)."""
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
    """Mengambil pohon direktori file audio dari asmr.one API dengan bypass header WAF."""
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
    Menyaring dan memilih hanya track cerita utama (本編) dari pohon direktori asmr.one:
    1. Filter hanya format audio valid.
    2. Jika di root langsung ada track bernomor urut (seperti RJ386444), pilih itu.
    3. Jika di dalam subfolder, utamakan folder '本編' / 'main' dan hindari varian (SE無, 原本, cuaca, sistem).
    4. Deduplikasi format: Jika ada MP3 dan WAV, utamakan MP3.
    5. Urutkan track secara kronologis alami.
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

    # 1. Kumpulkan semua audio yang ada di level root
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

    # Cek apakah root_audios memiliki pola nomor urut cerita (01, 02, ...)
    numbered_root = [a for a in root_audios if re.match(r'^\s*0?\d+', a["title"])]
    if len(numbered_root) >= 2 or (len(root_audios) > 0 and len(numbered_root) == len(root_audios)):
        # Jika root_audios seluruhnya adalah WAV/lossless berukuran gigantis, cek apakah ada folder MP3 resmi untuk 本編
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

    # 2. Skoring folder jika track berada dalam subfolder
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

    # Fallback terakhir jika tidak ada folder unggulan
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
    Mendeteksi semua track audio (Track 1, Track 2, ..., Omake, Bonus) untuk satu Kode RJ:
    1. Cek sumber utama: JapaneseASMR (.m3u8 master atau .mp3 multi-track).
    2. Jika tidak ditemukan di sumber utama, otomatis fallback ke asmr.one API via Smart Track Filter.
    """
    import re
    clean_id = rj_id.strip()
    if clean_id.startswith("http://") or clean_id.startswith("https://"):
        return [{"name": "Track 1", "url": clean_id, "referer": referer, "source": "direct"}]

    # 1. Cek apakah ada file master HLS .m3u8 di JapaneseASMR
    m3u8_url = f"https://v.weeab0o.xyz/{clean_id}.m3u8"
    if check_url_exists(m3u8_url, referer, user_agent):
        return [{"name": "Track 1", "url": m3u8_url, "referer": referer, "source": "japaneseasmr"}]

    found_tracks = []

    # 2. Cek Track 1 (.mp3) di JapaneseASMR
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

        # 3. Cek Track 2 s/d 20 (.mp3)
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

        # 4. Cek Omake / Bonus / Tokuten / EX (.mp3)
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

    # 5. Fallback ke asmr.one jika sumber JapaneseASMR tidak ditemukan
    num_id = re.sub(r'^[A-Za-z]+', '', clean_id)
    if num_id:
        asmrone_tree = fetch_asmrone_tree(num_id)
        if asmrone_tree:
            asmr_tracks = filter_smart_asmrone_tracks(asmrone_tree)
            if asmr_tracks:
                return asmr_tracks

    # Fallback terakhir
    return [{"name": "Track 1", "url": t1_candidates[0], "referer": referer, "source": "japaneseasmr"}]


def resolve_audio_url(rj_id, referer="https://japaneseasmr.com", user_agent="Mozilla/5.0"):
    """Mendeteksi single URL audio pertama."""
    tracks = discover_all_audio_tracks(rj_id, referer, user_agent)
    return tracks[0]["url"] if tracks else f"https://v.weeab0o.xyz/{rj_id}.mp3"


def get_precise_duration_seconds(file_path):
    """Mendapatkan durasi presisi berkas audio (dalam detik float) via ffprobe atau ffmpeg."""
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

    # Fallback ke ffmpeg -i
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
    """Mendeteksi codec audio dari berkas (misal 'aac', 'mp3', 'flac') via ffprobe."""
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


def generate_chapter_metadata(track_files, track_names=None, rj_id=None, temp_dir=None, log_func=print):
    """
    Membuat file metadata penanda bab FFMPEG (FFMETADATA1) dengan Smart Hybrid Chapter Mapping:
    - Kasus A (JapaneseASMR Master + Omake):
      Jika durasi track fisik pertama (track_files[0]) cocok dengan total durasi bab asmr.one (+- 2.5s),
      pecah track_files[0] menjadi bab-bab cerita dari asmr.one, lalu sambung track_files[1:] (omake/bonus) sebagai bab berikutnya.
    - Kasus B (Multi-track 1-to-1):
      Jika jumlah track fisik sama dengan jumlah track asmr.one dan total durasi cocok (+- 2.5s),
      sinkronkan nama bab dengan judul dari asmr.one.
    - Kasus C (Multi-track fisik murni):
      Jika > 1 file fisik dan tidak cocok dengan asmr.one, buat bab berdasarkan file fisik masing-masing.
    Mengembalikan: (path ke ffmetadata.txt, jumlah_bab) jika valid, atau (None, 0).
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

                        # KASUS A: Track 1 adalah audio kompilasi utama yang cocok dengan total bab asmr.one (+- 2.5s)
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

                            # Jika ada file fisik tambahan di disk (seperti Omake, Bonus, EX di track_files[1:])
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

                        # KASUS B: Total durasi seluruh file fisik cocok dengan total asmr.one dan jumlah track sama
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

    # KASUS C: Fallback Multi-track fisik murni (jika tidak cocok dengan asmr.one)
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
    Membuat berkas CUE sheet (.cue) berdampingan dengan berkas audio .mp3
    agar pemutar audio seperti Foobar2000, AIMP, MusicBee, dan VLC dapat mengenali
    dan menampilkan daftar bab (track splitting) secara instan.
    """
    if not chapters or len(chapters) <= 1:
        return None
    cue_path = os.path.splitext(output_audio_path)[0] + ".cue"
    audio_fname = os.path.basename(output_audio_path)
    meta = meta or {}
    artist = meta.get("cv") if meta.get("cv") and meta.get("cv") != "-" else "JapaneseASMR"
    album = meta.get("title") or os.path.splitext(audio_fname)[0]

    lines = [
        f'PERFORMER "{artist}"',
        f'TITLE "{album}"',
        f'FILE "{audio_fname}" MP3',
    ]
    for idx, ch in enumerate(chapters):
        t_num = idx + 1
        t_title = ch.get("title") or f"Track {t_num}"
        safe_title = t_title.replace('"', "'")
        ms = ch.get("start", 0)
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


def embed_cover_and_merge(track_files, cover_path, output_name, track_names=None, meta=None, rj_id=None, log_func=print):
    """
    Menggabungkan multi-track (jika ada), menyematkan cover art HD, metadata lengkap,
    serta menanamkan penanda bab (chapters) secara otomatis.
    Mendukung output berkas .m4a (dengan Apple/Nero chapter tracks) dan .mp3.
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

    # 1. Hasilkan file Chapter jika memenuhi syarat
    meta_chapter_file, num_chaps, parsed_chapters = generate_chapter_metadata(
        track_files, track_names=track_names, rj_id=clean_rj, temp_dir=temp_dir, log_func=log_func
    )
    if meta_chapter_file:
        cleanup_list.append(meta_chapter_file)
        if log_func:
            log_func(f"[i] Menyematkan {num_chaps} penanda bab (chapters) ke dalam {os.path.basename(output_name)}...")

    # 2. Siapkan input audio (Concat list jika multi-track, atau file langsung)
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

    # 3. Susun parameter FFmpeg dasar
    base_cmd = [ffmpeg_bin, "-hide_banner", "-loglevel", "error", "-y"]
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
        base_cmd.extend(["-map_metadata", str(chapter_input_idx)])

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

    # Analisis Codec Input untuk Smart Fast Remux (Mencegah Re-encode CPU berlebih)
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

        # Buat berkas CUE Sheet pendamping jika format MP3 agar bab terbaca di Foobar2000
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

