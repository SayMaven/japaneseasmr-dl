import os
import re
import subprocess
import sys
import urllib.request
from config_manager import (
    add_to_history,
    discover_all_audio_tracks,
    get_download_dir,
    load_config,
    resolve_audio_url,
    save_config,
    set_download_dir,
)

# Inisialisasi warna terminal ANSI untuk Windows / Linux / macOS
if sys.platform == "win32":
    os.system("")

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
    print(f"{CYAN}{BOLD}   JapaneseASMR Downloader (Terminal CLI Mode){RESET}")
    print(f"{CYAN}{BOLD}==================================================={RESET}\n")


def parse_rj_ids(input_text):
    """Mengekstrak list ID/Kode dari input (support pemisah koma, spasi, newline)."""
    if not input_text.strip():
        return [DEFAULT_ID]
    raw_tokens = re.split(r"[\s,;]+", input_text.strip())
    ids = [token.strip() for token in raw_tokens if token.strip()]
    return ids if ids else [DEFAULT_ID]


def download_cover(url, output_path):
    req = urllib.request.Request(
        url,
        headers={
            "Referer": REFERER,
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(req) as response:
        img_bytes = response.read()
    try:
        import io
        from PIL import Image
        with Image.open(io.BytesIO(img_bytes)) as pil_c:
            pil_c.convert("RGB").save(output_path, "JPEG", quality=92)
    except Exception:
        with open(output_path, "wb") as out_file:
            out_file.write(img_bytes)


def download_audio(audio_url, output_tmpl):
    cmd = [
        "yt-dlp",
        "-N", "16",
        "--downloader", "aria2c",
        "--fixup", "never",
        "--add-header", f"Referer: {REFERER}",
        "--add-header", f"Origin: {REFERER}",
        "--user-agent", USER_AGENT,
        audio_url,
        "-x",
        "--audio-format", "mp3",
        "-o", output_tmpl,
    ]
    subprocess.run(cmd, check=True)


def embed_cover_and_merge(track_files, cover_path, output_name, track_names=None):
    if len(track_files) > 1:
        temp_dir = os.path.dirname(track_files[0])
        concat_list_file = os.path.join(temp_dir, "concat_cli_list.txt")
        with open(concat_list_file, "w", encoding="utf-8") as f_concat:
            for tf in track_files:
                safe_p = os.path.abspath(tf).replace("\\", "/")
                f_concat.write(f"file '{safe_p}'\n")

        comment_val = f"Tracks: {len(track_files)} Gabungan ({', '.join(track_names)})" if track_names else f"Tracks: {len(track_files)} Gabungan"
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_file,
            "-i", cover_path,
            "-map", "0:a",
            "-map", "1:v",
            "-c:a", "libmp3lame",
            "-q:a", "2",
            "-c:v", "mjpeg",
            "-disposition:v:0", "attached_pic",
            "-id3v2_version", "3",
            "-metadata:s:v", "title=Album cover",
            "-metadata:s:v", "comment=Cover (front)",
            "-metadata", f"title={os.path.splitext(os.path.basename(output_name))[0]}",
            "-metadata", "artist=JapaneseASMR",
            "-metadata", f"comment={comment_val}",
            output_name,
        ]
        try:
            subprocess.run(cmd, check=True)
        finally:
            if os.path.exists(concat_list_file):
                try:
                    os.remove(concat_list_file)
                except OSError:
                    pass
    else:
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-y",
            "-i", track_files[0],
            "-i", cover_path,
            "-map", "0:a",
            "-map", "1:v",
            "-c:a", "copy",
            "-c:v", "mjpeg",
            "-disposition:v:0", "attached_pic",
            "-id3v2_version", "3",
            "-metadata:s:v", "title=Album cover",
            "-metadata:s:v", "comment=Cover (front)",
            "-metadata", f"title={os.path.splitext(os.path.basename(output_name))[0]}",
            "-metadata", "artist=JapaneseASMR",
            "-metadata", f"comment=Circle: JapaneseASMR",
            output_name,
        ]
        subprocess.run(cmd, check=True)


def cleanup_temp_files(temp_files):
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except OSError:
                pass


def process_single_id(rj_id, current_index, total_count):
    download_dir = get_download_dir()

    cover_url = f"https://pic.weeabo0.xyz/{rj_id}_img_main.jpg"
    final_output = os.path.join(download_dir, f"{rj_id}.mp3")

    progress_info = f"[{current_index}/{total_count}] " if total_count > 1 else ""

    print(f"\n{MAGENTA}{'-' * 51}{RESET}")
    print(f"{BOLD}{progress_info}Memproses: {CYAN}{rj_id}{RESET}")
    print(f" URL Cover     : {cover_url}")
    print(f" Folder Simpan : {download_dir}")
    print(f" File Output   : {final_output}")
    print(f"{MAGENTA}{'-' * 51}{RESET}\n")

    # Cek jika file sudah ada
    if os.path.exists(final_output):
        print(f"{YELLOW}[SKIP] File '{final_output}' sudah ada. Melewati proses download.{RESET}")
        return

    temp_dir = os.path.join(".cache", "temp")
    os.makedirs(temp_dir, exist_ok=True)

    temp_cover = os.path.join(temp_dir, f"temp_{rj_id}_cover.jpg")
    temp_files = [temp_cover]

    try:
        # 0. Deteksi Multi-Track & Omake
        print(f"{CYAN}[0/3] Mendeteksi track audio & omake...{RESET}")
        tracks = discover_all_audio_tracks(rj_id, REFERER, USER_AGENT)
        track_names = [t["name"] for t in tracks]
        if len(tracks) > 1:
            print(f"{GREEN}[i] Terdeteksi {len(tracks)} track: {', '.join(track_names)}. Semua akan digabung otomatis!{RESET}")
        else:
            print(f"{GREEN}[i] Terdeteksi 1 track utama.{RESET}")

        # 1. Download Cover
        print(f"{CYAN}[1/3] Mendownload cover image...{RESET}")
        download_cover(cover_url, temp_cover)

        # 2. Download Semua Track
        downloaded_track_files = []
        for t_idx, track_info in enumerate(tracks, start=1):
            t_name = track_info["name"]
            t_url = track_info["url"]
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
            download_audio(t_url, t_out_tmpl)

            # Deteksi file audio yang berhasil dibuat
            possible_files = [
                t_final_mp3,
                os.path.join(temp_dir, f"temp_{rj_id}_t{t_idx}_.mp3"),
                os.path.join(temp_dir, f"temp_{rj_id}_t{t_idx}.(ext)s.mp3"),
                os.path.join(temp_dir, f"temp_{rj_id}_t{t_idx}.mp4"),
            ]
            actual_file = next((f for f in possible_files if os.path.exists(f)), None)

            if not actual_file:
                raise FileNotFoundError(f"File audio untuk {t_name} gagal diunduh.")
            downloaded_track_files.append(actual_file)

        # 3. Merge Tracks & Embed Cover Art
        if len(downloaded_track_files) > 1:
            print(f"{CYAN}[3/3] Menggabungkan {len(tracks)} track & menyematkan cover art...{RESET}")
        else:
            print(f"{CYAN}[3/3] Menyematkan cover art ke file MP3...{RESET}")
        embed_cover_and_merge(downloaded_track_files, temp_cover, final_output, track_names)

        # Simpan ke riwayat unduhan
        add_to_history(
            rjid=rj_id,
            title=rj_id,
            cv="-",
            circle="-",
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
    run_cli()
