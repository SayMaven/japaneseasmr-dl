import os
import re
import subprocess
import sys
import urllib.request
from config_manager import (
    add_to_history,
    discover_all_audio_tracks,
    embed_cover_and_merge,
    get_audio_codec,
    get_audio_format,
    get_bin_executable,
    get_download_dir,
    load_config,
    resolve_audio_url,
    save_config,
    set_download_dir,
)
from dlsite_scraper import fetch_dlsite_metadata, resolve_best_cover_url, sanitize_filename

# Inisialisasi warna terminal ANSI & konfigurasi encoding UTF-8 untuk Windows
if sys.platform == "win32":
    os.system("")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Kode Warna ANSI
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RED = "\033[91m"
MAGENTA = "\033[95m"

REFERER = "https://japaneseasmr.com"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
DEFAULT_ID = "RJ01673437"


def print_banner():
    print(f"\n{CYAN}{BOLD}==================================================={RESET}")
    print(f"{CYAN}{BOLD}   JapaneseASMR Downloader v1.1.0 (Terminal CLI)   {RESET}")
    print(f"{CYAN}{BOLD}==================================================={RESET}\n")


def parse_rj_ids(input_text):
    """Mengekstrak list ID/Kode dari input (support pemisah koma, spasi, newline)."""
    if not input_text.strip():
        return [DEFAULT_ID]
    raw_tokens = re.split(r"[\s,;]+", input_text.strip())
    ids = [token.strip() for token in raw_tokens if token.strip()]
    return ids if ids else [DEFAULT_ID]


def download_cover(cover_url, output_path, rj_id=None, dlsite_cover=None):
    candidates = []
    if cover_url:
        candidates.append(cover_url)
    if rj_id:
        alt = resolve_best_cover_url(rj_id, dlsite_cover)
        if alt and alt not in candidates:
            candidates.append(alt)
        num_id = re.sub(r'^[A-Za-z]+', '', rj_id)
        if num_id:
            asmr_c = f"https://api.asmr.one/api/cover/{num_id}.jpg?type=main"
            if asmr_c not in candidates:
                candidates.append(asmr_c)

    for c_url in candidates:
        try:
            cover_ref = "https://www.dlsite.com" if "dlsite" in c_url else ("https://asmr.one/" if "asmr.one" in c_url else REFERER)
            req = urllib.request.Request(
                c_url,
                headers={
                    "Referer": cover_ref,
                    "User-Agent": USER_AGENT,
                    "Accept-Language": "zh-CN,zh;q=0.9,ja;q=0.8,en;q=0.7",
                },
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                img_bytes = response.read()
            try:
                import io
                from PIL import Image
                with Image.open(io.BytesIO(img_bytes)) as pil_c:
                    pil_c.convert("RGB").save(output_path, "JPEG", quality=92)
            except Exception:
                with open(output_path, "wb") as out_file:
                    out_file.write(img_bytes)
            return True
        except Exception:
            continue

    try:
        from PIL import Image
        blank_img = Image.new("RGB", (600, 600), color=(30, 30, 46))
        blank_img.save(output_path, "JPEG", quality=90)
        return True
    except Exception:
        return False


def download_audio(audio_url, output_tmpl, referer=REFERER):
    import time
    ytdlp_bin = get_bin_executable("yt-dlp")
    aria2c_bin = get_bin_executable("aria2c")
    ffmpeg_bin = get_bin_executable("ffmpeg")
    ffmpeg_dir = os.path.dirname(os.path.abspath(ffmpeg_bin))

    cmd = [
        ytdlp_bin,
        "--ffmpeg-location", ffmpeg_dir,
        "--socket-timeout", "60",
        "--retries", "10",
        "--extractor-retries", "5",
        "--fragment-retries", "10",
        "--retry-sleep", "3",
        "-N", "16",
        "--downloader", f"default:{aria2c_bin}",
        "--downloader", "dash,m3u8:native",
        "--downloader-args", "aria2c:-s 16 -x 16 -k 1M --file-allocation=none --summary-interval=1 --timeout=60 --max-tries=10 --retry-wait=3 --continue=true",
        "--fixup", "never",
        "--add-header", f"Referer: {referer}",
        "--add-header", f"Origin: {referer}",
        "--add-header", "Accept-Language: zh-CN,zh;q=0.9,ja;q=0.8,en;q=0.7",
        "--user-agent", USER_AGENT,
        audio_url,
        "-o", output_tmpl,
    ]

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            if attempt > 1:
                print(f"{YELLOW}[i] Mengulang unduhan (Percobaan {attempt}/{max_attempts})...{RESET}")
                time.sleep(2)
            subprocess.run(cmd, check=True)
            return
        except subprocess.CalledProcessError:
            if attempt == max_attempts:
                raise



def cleanup_temp_files(temp_files):
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass


def process_single_id(rj_id, current_index, total_count):
    cfg = load_config()
    download_dir = get_download_dir()

    # Ambil metadata resmi dari DLsite
    print(f"\n{CYAN}[*] Mengambil informasi karya dari DLsite...{RESET}")
    meta = fetch_dlsite_metadata(rj_id)
    title = meta.get("title", rj_id)
    cv = meta.get("cv", "-")
    circle = meta.get("circle", "-")
    genre = meta.get("genre", "-")
    age_rating = meta.get("age_rating", "-")
    cover_url = meta.get("cover_url") or f"https://pic.weeabo0.xyz/{rj_id}_img_main.jpg"

    configured_fmt = get_audio_format()
    clean_title = sanitize_filename(title) if (cfg.get("use_detailed_filename") and title and title != rj_id) else ""
    base_fname = f"[{rj_id}] {clean_title}" if clean_title else rj_id

    # Cek jika file sudah ada
    if configured_fmt == "auto":
        possible_existing = [
            os.path.join(download_dir, f"{base_fname}.m4a"),
            os.path.join(download_dir, f"{base_fname}.mp3"),
            os.path.join(download_dir, f"{rj_id}.m4a"),
            os.path.join(download_dir, f"{rj_id}.mp3"),
        ]
    else:
        possible_existing = [os.path.join(download_dir, f"{base_fname}.{configured_fmt}")]

    existing_file = next((f for f in possible_existing if os.path.exists(f) and os.path.getsize(f) > 0), None)
    if existing_file:
        print(f"{YELLOW}[SKIP] File '{os.path.basename(existing_file)}' sudah ada. Melewati proses download.{RESET}")
        return

    final_output = os.path.join(download_dir, f"{base_fname}.{configured_fmt if configured_fmt != 'auto' else 'm4a'}")

    progress_info = f"[{current_index}/{total_count}] " if total_count > 1 else ""

    print(f"\n{MAGENTA}{'-' * 51}{RESET}")
    print(f"{BOLD}{progress_info}Memproses      : {CYAN}{rj_id}{RESET}")
    print(f" Judul Karya    : {GREEN}{title}{RESET}")
    print(f" CV / Seiyuu    : {YELLOW}{cv}{RESET}")
    print(f" Circle / Maker : {circle}")
    print(f" Genre / Rating : {genre} [{age_rating}]")
    print(f" Folder Simpan  : {download_dir}")
    print(f" Format Mode    : {configured_fmt.upper() if configured_fmt != 'auto' else 'Otomatis (Fast Remux)'}")
    print(f"{MAGENTA}{'-' * 51}{RESET}\n")

    temp_dir = os.path.join(".cache", "temp")
    os.makedirs(temp_dir, exist_ok=True)

    temp_cover = os.path.join(temp_dir, f"temp_{rj_id}_cover.jpg")
    temp_files = [temp_cover]

    try:
        # 0. Deteksi Multi-Track & Omake
        print(f"{CYAN}[0/3] Mendeteksi track audio & omake...{RESET}")
        tracks = discover_all_audio_tracks(rj_id, REFERER, USER_AGENT)
        track_names = [t["name"] for t in tracks]
        source_type = tracks[0].get("source", "japaneseasmr") if tracks else "japaneseasmr"
        if source_type == "asmr.one":
            print(f"{CYAN}[i] Sumber audio: asmr.one (Fallback aktif){RESET}")
        else:
            print(f"{CYAN}[i] Sumber audio: JapaneseASMR (Utama){RESET}")

        if len(tracks) > 1:
            print(f"{GREEN}[i] Terdeteksi {len(tracks)} track: {', '.join(track_names)}. Semua akan digabung otomatis!{RESET}")
        else:
            print(f"{GREEN}[i] Terdeteksi 1 track utama.{RESET}")

        # 1. Download Cover
        print(f"{CYAN}[1/3] Mendownload cover image...{RESET}")
        download_cover(cover_url, temp_cover, rj_id=rj_id, dlsite_cover=meta.get("dlsite_cover_url"))

        # 2. Download Semua Track
        downloaded_track_files = []
        for t_idx, track_info in enumerate(tracks, start=1):
            t_name = track_info["name"]
            t_url = track_info["url"]
            t_ref = track_info.get("referer", REFERER)
            t_out_tmpl = os.path.join(temp_dir, f"temp_{rj_id}_t{t_idx}.%(ext)s")
            t_final_mp3 = os.path.join(temp_dir, f"temp_{rj_id}_t{t_idx}.mp3")

            temp_files.extend([
                t_final_mp3,
                os.path.join(temp_dir, f"temp_{rj_id}_t{t_idx}_.mp3"),
                os.path.join(temp_dir, f"temp_{rj_id}_t{t_idx}.mp4"),
                os.path.join(temp_dir, f"temp_{rj_id}_t{t_idx}.temp.mp4"),
                os.path.join(temp_dir, f"temp_{rj_id}_t{t_idx}.(ext)s.mp3"),
            ])

            print(f"{CYAN}[2/3] Mengunduh {t_name} [{t_idx}/{len(tracks)}] (16 koneksi)...{RESET}")
            download_audio(t_url, t_out_tmpl, referer=t_ref)

            # Deteksi file audio yang berhasil dibuat (berbagai format audio asli)
            prefix = f"temp_{rj_id}_t{t_idx}."
            candidates = [
                os.path.join(temp_dir, f) for f in os.listdir(temp_dir)
                if f.startswith(prefix) and not f.endswith((".part", ".temp", ".ytdl", ".aria2"))
            ]
            actual_file = next((f for f in candidates if os.path.isfile(f) and os.path.getsize(f) > 0), None)
            if actual_file:
                temp_files.append(actual_file)

            if not actual_file:
                raise FileNotFoundError(f"File audio untuk {t_name} gagal diunduh.")
            downloaded_track_files.append(actual_file)

        # 3. Tentukan nama dan format file output akhir (Smart Native Container)
        if configured_fmt == "auto":
            first_codec = get_audio_codec(downloaded_track_files[0]) if downloaded_track_files else ""
            out_ext = ".m4a" if first_codec == "aac" else (".mp3" if first_codec == "mp3" else ".m4a")
            final_output = os.path.join(download_dir, f"{base_fname}{out_ext}")
        else:
            final_output = os.path.join(download_dir, f"{base_fname}.{configured_fmt}")

        # 3. Merge Tracks & Embed Cover Art + Metadata & Chapters
        if len(downloaded_track_files) > 1:
            print(f"{CYAN}[3/3] Menggabungkan {len(downloaded_track_files)} track, menyematkan penanda bab & metadata...{RESET}")
        else:
            print(f"{CYAN}[3/3] Menyematkan cover art, penanda bab & metadata...{RESET}")
        embed_cover_and_merge(
            downloaded_track_files,
            temp_cover,
            final_output,
            track_names=track_names,
            meta=meta,
            rj_id=rj_id,
            log_func=lambda msg: print(f"{CYAN}{msg}{RESET}"),
        )

        # Simpan ke riwayat unduhan
        add_to_history(
            rjid=rj_id,
            title=title,
            cv=cv,
            circle=circle,
            genre=genre,
            age_rating=age_rating,
            cover_url=cover_url,
            output_path=final_output,
            temp_cover_path=temp_cover,
        )

        print(f"\n{GREEN}{BOLD}[SUCCESS] Selesai: {final_output}{RESET}")

    except Exception as e:
        print(f"\n{RED}{BOLD}[ERROR] Gagal memproses {rj_id}: {e}{RESET}")

    finally:
        cleanup_temp_files(temp_files)


def run_cli():
    print_banner()
    cfg = load_config()
    current_dir = get_download_dir()
    default_id = cfg.get("default_id", DEFAULT_ID)

    print(f"Folder download aktif: {YELLOW}{os.path.abspath(current_dir)}{RESET}")
    ubah_folder = input(f"Ingin mengubah folder simpan? (y/N): ").strip().lower()
    if ubah_folder == "y":
        folder_baru = input("Masukkan path folder download baru: ").strip()
        if folder_baru:
            set_download_dir(folder_baru)
            print(f"{GREEN}Folder berhasil diubah ke:{RESET} {folder_baru}\n")

    user_input = input(
        f"Masukkan satu / banyak Kode RJ (contoh: RJ01673437, RJ01678243)\n"
        f"[Tekan Enter untuk default '{default_id}']: "
    )

    rj_ids = parse_rj_ids(user_input)
    total_count = len(rj_ids)

    print(f"\n{CYAN}{BOLD}Memulai antrean unduhan ({total_count} item)...{RESET}")

    for idx, rjid in enumerate(rj_ids, start=1):
        process_single_id(rjid, idx, total_count)

    print(f"\n{GREEN}{BOLD}==================================================={RESET}")
    print(f"{GREEN}{BOLD}   Semua proses dalam antrean telah selesai!{RESET}")
    print(f"{GREEN}{BOLD}==================================================={RESET}\n")


if __name__ == "__main__":
    try:
        run_cli()
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}[!] Dibatalkan oleh pengguna. Keluar...{RESET}\n")
        sys.exit(0)

