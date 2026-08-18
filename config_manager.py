import json
import os
import shutil
import time
from PIL import Image

CONFIG_FILE = "config.json"
HISTORY_FILE = "history.json"
CACHE_DIR = os.path.join(".cache", "covers")

DEFAULT_CONFIG = {
    "download_dir": "downloads",
    "use_detailed_filename": False,
    "default_id": "RJ01673437",
}


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


def discover_all_audio_tracks(rj_id, referer="https://japaneseasmr.com", user_agent="Mozilla/5.0"):
    """
    Mendeteksi semua track audio (Track 1, Track 2, ..., Omake, Bonus) untuk satu Kode RJ.
    - Jika stream .m3u8 tersedia, dipastikan hanya 1 track (langsung dikembalikan tanpa scan multi-track).
    - Jika stream bertipe .mp3 direct, sistem akan memindai kemungkinan multi-track dan omake.
    """
    clean_id = rj_id.strip()
    if clean_id.startswith("http://") or clean_id.startswith("https://"):
        return [{"name": "Track 1", "url": clean_id}]

    # 1. Cek apakah ada file master HLS .m3u8 (m3u8 selalu 1 track tunggal utuh)
    m3u8_url = f"https://v.weeab0o.xyz/{clean_id}.m3u8"
    if check_url_exists(m3u8_url, referer, user_agent):
        return [{"name": "Track 1", "url": m3u8_url}]

    found_tracks = []

    # 2. Cek Track 1 (.mp3)
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
        found_tracks.append({"name": "Track 1", "url": t1_url})
    else:
        found_tracks.append({"name": "Track 1", "url": t1_candidates[0]})

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
            found_tracks.append({"name": f"Track {track_num}", "url": matched_url})
        else:
            if track_num >= 4:
                # Jika track berturut-turut tidak ada, hentikan scanning angka
                break

    # 4. Cek Omake / Bonus / Tokuten (.mp3)
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
    ]
    seen_urls = {t["url"] for t in found_tracks}
    for om_name, om_url in omake_patterns:
        if om_url not in seen_urls and check_url_exists(om_url, referer, user_agent):
            found_tracks.append({"name": om_name, "url": om_url})
            seen_urls.add(om_url)

    return found_tracks


def resolve_audio_url(rj_id, referer="https://japaneseasmr.com", user_agent="Mozilla/5.0"):
    """Mendeteksi single URL audio pertama."""
    tracks = discover_all_audio_tracks(rj_id, referer, user_agent)
    return tracks[0]["url"] if tracks else f"https://v.weeab0o.xyz/{rj_id}.mp3"
