import os
import re
import subprocess
import sys
import urllib.request

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
DEFAULT_ID = "RJ01538146"
OUTPUT_DIR = "downloads"


def print_banner():
    print(f"\n{CYAN}{BOLD}==================================================={RESET}")
    print(f"{CYAN}{BOLD}   JapaneseASMR Downloader + Cover Art Embedder{RESET}")
    print(f"{CYAN}{BOLD}==================================================={RESET}\n")


def parse_rj_ids(input_text):
    """Mengekstrak list ID/Kode dari input (support pemisah koma, spasi, newline)."""
    if not input_text.strip():
        return [DEFAULT_ID]
    # Pisahkan berdasarkan koma, spasi, atau titik koma
    raw_tokens = re.split(r"[\s,;]+", input_text.strip())
    # Bersihkan token kosong
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
    with urllib.request.urlopen(req) as response, open(output_path, "wb") as out_file:
        out_file.write(response.read())


def download_audio(m3u8_url, output_tmpl):
    cmd = [
        "yt-dlp",
        "-N", "16",
        "--downloader", "aria2c",
        "--fixup", "never",
        "--add-header", f"Referer: {REFERER}",
        "--add-header", f"Origin: {REFERER}",
        "--user-agent", USER_AGENT,
        m3u8_url,
        "-x",
        "--audio-format", "mp3",
        "-o", output_tmpl,
    ]
    subprocess.run(cmd, check=True)


def embed_cover(audio_path, cover_path, output_name):
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", audio_path,
        "-i", cover_path,
        "-map", "0:a",
        "-map", "1:v",
        "-c", "copy",
        "-id3v2_version", "3",
        "-metadata:s:v", "title=Album cover",
        "-metadata:s:v", "comment=Cover (front)",
        "-metadata", f"title={os.path.splitext(os.path.basename(output_name))[0]}",
        "-metadata", "artist=JapaneseASMR",
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
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    m3u8_url = f"https://v.weeab0o.xyz/{rj_id}.m3u8"
    cover_url = f"https://pic.weeabo0.xyz/{rj_id}_img_main.jpg"
    final_output = os.path.join(OUTPUT_DIR, f"{rj_id}.mp3")

    progress_info = f"[{current_index}/{total_count}] " if total_count > 1 else ""

    print(f"\n{MAGENTA}{'-' * 51}{RESET}")
    print(f"{BOLD}{progress_info}Memproses: {CYAN}{rj_id}{RESET}")
    print(f" URL M3U8    : {m3u8_url}")
    print(f" URL Cover   : {cover_url}")
    print(f" File Output : {final_output}")
    print(f"{MAGENTA}{'-' * 51}{RESET}\n")

    # Fitur 4: Cek jika file sudah ada
    if os.path.exists(final_output):
        print(f"{YELLOW}[SKIP] File '{final_output}' sudah ada. Melewati proses download.{RESET}")
        return

    temp_cover = f"temp_{rj_id}_cover.jpg"
    temp_audio = f"temp_{rj_id}_audio.mp3"
    temp_tmpl = f"temp_{rj_id}_audio.%(ext)s"

    temp_files = [
        temp_cover,
        temp_audio,
        f"temp_{rj_id}_audio.mp4",
        f"temp_{rj_id}_audio.temp.mp4",
        f"temp_{rj_id}_audio.(ext)s.mp3",
    ]

    try:
        print(f"{CYAN}[1/3] Mendownload cover image...{RESET}")
        download_cover(cover_url, temp_cover)

        print(f"{CYAN}[2/3] Mendownload stream audio (16 parallel connections)...{RESET}")
        download_audio(m3u8_url, temp_tmpl)

        if not os.path.exists(temp_audio):
            raise FileNotFoundError("File audio sementara tidak ditemukan.")

        print(f"{CYAN}[3/3] Menyematkan thumbnail ke metadata MP3...{RESET}")
        embed_cover(temp_audio, temp_cover, final_output)

        print(f"\n{GREEN}{BOLD}==================================================={RESET}")
        print(f"{GREEN}{BOLD}  SUKSES! File tersimpan di: {final_output}{RESET}")
        print(f"{GREEN}{BOLD}==================================================={RESET}")

    except Exception as e:
        print(f"\n{RED}[ERROR] Gagal memproses {rj_id}: {e}{RESET}")

    finally:
        cleanup_temp_files(temp_files)


def main():
    while True:
        print_banner()

        try:
            user_input = input(
                f"{BOLD}Masukkan Kode/Angka RJ (Bisa beberapa dipisah spasi/koma, Enter untuk {DEFAULT_ID}): {RESET}"
            ).strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{YELLOW}Program dihentikan.{RESET}")
            break

        rj_ids = parse_rj_ids(user_input)
        total_count = len(rj_ids)

        if total_count > 1:
            print(f"\n{CYAN}[INFO] Terdeteksi {total_count} ID dalam antrean download.{RESET}")

        for idx, rj_id in enumerate(rj_ids, start=1):
            process_single_id(rj_id, idx, total_count)

        print(f"\n{GREEN}--- Semua antrean batch selesai! ---{RESET}\n")


if __name__ == "__main__":
    main()
