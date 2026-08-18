import os
import re
import subprocess
import sys
import urllib.request
from config_manager import (
    add_to_history,
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
    print(f"{CYAN}{BOLD}   JapaneseASMR Downloader + Cover Art Embedder{RESET}")
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
    download_dir = get_download_dir()

    audio_url = resolve_audio_url(rj_id, REFERER, USER_AGENT)
    cover_url = f"https://pic.weeabo0.xyz/{rj_id}_img_main.jpg"
    final_output = os.path.join(download_dir, f"{rj_id}.mp3")

    progress_info = f"[{current_index}/{total_count}] " if total_count > 1 else ""

    print(f"\n{MAGENTA}{'-' * 51}{RESET}")
    print(f"{BOLD}{progress_info}Memproses: {CYAN}{rj_id}{RESET}")
    print(f" URL Audio   : {audio_url}")
    print(f" URL Cover   : {cover_url}")
    print(f" Folder Simpan : {download_dir}")
    print(f" File Output : {final_output}")
    print(f"{MAGENTA}{'-' * 51}{RESET}\n")

    # Cek jika file sudah ada
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
        download_audio(audio_url, temp_tmpl)

        if not os.path.exists(temp_audio):
            raise FileNotFoundError("File audio sementara tidak ditemukan.")

        print(f"{CYAN}[3/3] Menyematkan thumbnail ke metadata MP3...{RESET}")
        embed_cover(temp_audio, temp_cover, final_output)

        # Catat ke history dan cache cover
        add_to_history(
            rjid=rj_id,
            title=rj_id,
            cv="-",
            circle="-",
            cover_url=cover_url,
            output_path=final_output,
            temp_cover_path=temp_cover,
        )

        print(f"\n{GREEN}{BOLD}==================================================={RESET}")
        print(f"{GREEN}{BOLD}  SUKSES! File tersimpan di: {final_output}{RESET}")
        print(f"{GREEN}{BOLD}==================================================={RESET}")

    except Exception as e:
        print(f"\n{RED}[ERROR] Gagal memproses {rj_id}: {e}{RESET}")

    finally:
        cleanup_temp_files(temp_files)


def run_cli():
    """Menjalankan antarmuka berbasis Terminal / CLI."""
    while True:
        print_banner()
        current_dir = get_download_dir()
        print(f"{CYAN}📁 Folder Simpan Saat Ini:{RESET} {os.path.abspath(current_dir)}\n")

        try:
            user_input = input(
                f"{BOLD}Masukkan Kode RJ / 'dir' untuk ganti folder / Enter ({DEFAULT_ID}): {RESET}"
            ).strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{YELLOW}Program dihentikan.{RESET}")
            break

        if user_input.lower() == "dir":
            new_path = input("Masukkan path folder baru: ").strip()
            if new_path:
                set_download_dir(new_path)
                print(f"{GREEN}[OK] Folder download diperbarui ke: {new_path}{RESET}\n")
            continue

        rj_ids = parse_rj_ids(user_input)
        total_count = len(rj_ids)

        if total_count > 1:
            print(f"\n{CYAN}[INFO] Terdeteksi {total_count} ID dalam antrean download.{RESET}")

        for idx, rj_id in enumerate(rj_ids, start=1):
            process_single_id(rj_id, idx, total_count)

        print(f"\n{GREEN}--- Semua antrean batch selesai! ---{RESET}\n")


def run_gui():
    """Menjalankan antarmuka Desktop GUI dari gui.py."""
    try:
        from gui import JapaneseASMRApp
        print(f"{GREEN}[INFO] Membuka antarmuka Desktop GUI...{RESET}")
        app = JapaneseASMRApp()
        app.mainloop()
    except ImportError as e:
        print(f"{RED}[ERROR] Gagal memuat GUI: {e}{RESET}")
        print(f"{YELLOW}Menjalankan mode CLI sebagai gantinya...{RESET}")
        run_cli()


def main():
    # Cek jika dipanggil lewat argumen flag
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ("--gui", "-g"):
            run_gui()
            return
        elif arg in ("--cli", "-c"):
            run_cli()
            return

    # Tampilkan menu pilihan mode
    print_banner()
    print(f"{BOLD}Silakan pilih mode yang ingin dijalankan:{RESET}")
    print(f"  {CYAN}[1]{RESET} Mode Desktop GUI {BOLD}(Preview Cover, Antrean, & Riwayat){RESET}")
    print(f"  {CYAN}[2]{RESET} Mode Terminal CLI {BOLD}(Cepat & Ringan){RESET}")
    print(f"  {CYAN}[0]{RESET} Keluar")
    print()

    try:
        choice = input(f"{BOLD}Pilih mode [1/2] (Tekan Enter untuk GUI): {RESET}").strip()
    except (KeyboardInterrupt, EOFError):
        print(f"\n{YELLOW}Keluar.{RESET}")
        return

    if choice == "2":
        run_cli()
    elif choice == "0":
        print(f"{YELLOW}Sampai jumpa!{RESET}")
        return
    else:
        run_gui()


if __name__ == "__main__":
    main()
