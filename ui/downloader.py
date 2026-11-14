import io
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request

from PIL import Image

from config_manager import (
    add_to_history,
    discover_all_audio_tracks,
    embed_cover_and_merge,
    get_audio_codec,
    get_audio_format,
    get_bin_executable,
    get_download_dir,
    write_cue_sheet,
)
from dlsite_scraper import (
    fetch_dlsite_metadata,
    resolve_best_cover_url,
    sanitize_filename,
)
from i18n import t
from ui.constants import (
    REFERER,
    RE_ARIA2_PROGRESS,
    RE_FRAG_PROGRESS,
    RE_YTDLP_PROGRESS,
    USER_AGENT,
)
from ui.dialogs import show_dark_error, show_dark_info, show_dark_warning


class DownloadWorkerMixin:
    """Mixin untuk mengelola proses download latar belakang, status progress, dan penghentian tugas."""
    def _update_progress(self, val_pct, status_text=None, speed=None, eta=None, size_str=None):
        def _apply():
            clamped = max(0.0, min(100.0, float(val_pct)))
            if hasattr(self, "progress_bar"):
                if hasattr(self.progress_bar, "set"):
                    self.progress_bar.set(clamped / 100.0)
                else:
                    self.progress_bar["value"] = clamped
            if hasattr(self, "lbl_progress_pct"):
                self.lbl_progress_pct.configure(text=f"{int(clamped)}%")
            if status_text and hasattr(self, "lbl_progress_status"):
                self.lbl_progress_status.configure(text=f"Status: {status_text}")
            if speed is not None and hasattr(self, "lbl_progress_speed"):
                self.lbl_progress_speed.configure(text=speed)
            if eta is not None and hasattr(self, "lbl_progress_eta"):
                self.lbl_progress_eta.configure(text=eta)
            if size_str is not None and hasattr(self, "lbl_progress_size"):
                self.lbl_progress_size.configure(text=size_str)
        self.after(0, _apply)

    def _start_download_thread(self):
        if self.is_downloading:
            return
        if not self.queue_items:
            show_dark_info(self, "Informasi", "Silakan tambahkan kode RJ ke antrean terlebih dahulu.")
            return

        self.is_downloading = True
        self.stop_requested = False
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")

        threading.Thread(target=self._download_worker, daemon=True).start()

    def _stop_downloads(self):
        self.stop_requested = True
        self._log("[!] Menghentikan proses download seketika...")
        self.stop_btn.config(state="disabled")

        # 1. Kill subprocess aktif secara paksa beserta anak-anaknya (yt-dlp, aria2c, ffmpeg)
        if self.current_process and self.current_process.poll() is None:
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(self.current_process.pid)],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                else:
                    self.current_process.kill()
            except Exception:
                pass
            self.current_process = None

        # 2. Pastikan process aria2c / yt-dlp / ffmpeg yatim dimatikan
        if sys.platform == "win32":
            for p_name in ["aria2c.exe", "yt-dlp.exe", "ffmpeg.exe"]:
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/IM", p_name],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                except Exception:
                    pass

        # 3. Bersihkan sampah part & temp files di .cache/temp/
        temp_dir = os.path.join(".cache", "temp")
        if os.path.exists(temp_dir):
            for fname in os.listdir(temp_dir):
                fpath = os.path.join(temp_dir, fname)
                try:
                    if os.path.isfile(fpath):
                        os.remove(fpath)
                except OSError:
                    pass

        self._update_progress(0, "Download Dihentikan")

    def _download_worker(self):
        download_dir = get_download_dir()
        os.makedirs(download_dir, exist_ok=True)
        total_items = len(self.queue_items)
        self._update_progress(0, f"Mempersiapkan {total_items} item...")

        for idx, item in enumerate(self.queue_items):
            if self.stop_requested:
                break

            item_step = 100.0 / max(1, total_items)
            base_pct = idx * item_step

            if item["status"] == "Selesai":
                self._update_progress((idx + 1) * item_step, f"[{idx+1}/{total_items}] Selesai (Dilewati)")
                continue

            rjid = item["rjid"]
            title = item.get("title", "")

            # Nama File Output & Cek apakah sudah pernah diunduh
            configured_fmt = get_audio_format()
            clean_title = sanitize_filename(title) if (self.opt_detailed_name.get() and title and title != "Memuat info..." and title != rjid) else ""
            base_fname = f"[{rjid}] {clean_title}" if clean_title else rjid

            if configured_fmt == "auto":
                possible_existing = [
                    os.path.join(download_dir, f"{base_fname}.m4a"),
                    os.path.join(download_dir, f"{base_fname}.mp3"),
                    os.path.join(download_dir, f"{rjid}.m4a"),
                    os.path.join(download_dir, f"{rjid}.mp3"),
                ]
            else:
                possible_existing = [os.path.join(download_dir, f"{base_fname}.{configured_fmt}")]

            existing_file = next((f for f in possible_existing if os.path.exists(f) and os.path.getsize(f) > 0), None)
            if existing_file:
                self._log(f"[SKIP] File '{os.path.basename(existing_file)}' sudah ada.")
                item["status"] = "Selesai"
                self.after(0, lambda i=idx: self.tree.set(str(i), "status", "Selesai (Ada)"))
                self._update_progress((idx + 1) * item_step, f"[{idx+1}/{total_items}] Selesai (Sudah Ada)")
                continue

            # Update status ke downloading
            item["status"] = "Downloading"
            self.after(0, lambda i=idx: self.tree.set(str(i), "status", "Mengunduh..."))
            self.after(0, lambda i=idx: self.tree.selection_set(str(i)))

            cover_url = item.get("cover_url")
            if not cover_url or "weeabo" in cover_url:
                cover_url = resolve_best_cover_url(rjid, item.get("dlsite_cover_url"))
                item["cover_url"] = cover_url

            temp_dir = os.path.join(".cache", "temp")
            os.makedirs(temp_dir, exist_ok=True)

            temp_cover = os.path.join(temp_dir, f"temp_{rjid}_cover.jpg")
            temp_files = [temp_cover]

            try:
                self._log(f"\n--- [{idx+1}/{total_items}] Memproses {rjid} ---")

                # 0. Deteksi Semua Track (Multi-track & Omake / asmr.one fallback)
                self._update_progress(base_pct + item_step * 0.05, f"[{idx+1}/{total_items}] Memindai track audio...")
                self._log("[0/3] Mendeteksi jumlah track audio...")
                tracks = discover_all_audio_tracks(rjid, REFERER, USER_AGENT)
                track_names = [t["name"] for t in tracks]
                source_type = tracks[0].get("source", "japaneseasmr") if tracks else "japaneseasmr"
                if source_type == "asmr.one":
                    self._log(f"[i] Sumber audio: asmrone (Fallback aktif)")
                else:
                    self._log(f"[i] Sumber audio: JapaneseASMR (Utama)")

                if len(tracks) > 1:
                    self._log(f"[i] Terdeteksi {len(tracks)} track ({', '.join(track_names)}). Semua akan digabung otomatis!")
                else:
                    self._log(f"[i] Terdeteksi 1 track audio.")

                if self.stop_requested:
                    break

                # 1. Download & Standardize Cover to JPEG (agar terbaca Windows Explorer)
                self._update_progress(base_pct + item_step * 0.15, f"[{idx+1}/{total_items}] Mengunduh cover art...")
                self._log("[1/3] Mengunduh cover art...")

                cache_cover_file = os.path.join(".cache", "covers", f"{rjid}.jpg")
                cover_downloaded = False

                if os.path.exists(cache_cover_file):
                    try:
                        with Image.open(cache_cover_file) as pil_c:
                            pil_c.convert("RGB").save(temp_cover, "JPEG", quality=92)
                        cover_downloaded = True
                    except Exception:
                        pass

                if not cover_downloaded:
                    candidates = []
                    if cover_url:
                        candidates.append(cover_url)
                    alt_c = resolve_best_cover_url(rjid, item.get("dlsite_cover_url"))
                    if alt_c and alt_c not in candidates:
                        candidates.append(alt_c)
                    num_id = re.sub(r'^[A-Za-z]+', '', rjid)
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
                            with urllib.request.urlopen(req, timeout=10) as resp:
                                img_bytes = resp.read()
                            with Image.open(io.BytesIO(img_bytes)) as pil_c:
                                pil_c.convert("RGB").save(temp_cover, "JPEG", quality=92)
                                os.makedirs(os.path.join(".cache", "covers"), exist_ok=True)
                                pil_c.convert("RGB").save(cache_cover_file, "JPEG", quality=85)
                            cover_downloaded = True
                            break
                        except Exception:
                            continue

                if not cover_downloaded:
                    self._log("[!] Cover art online tidak ditemukan, menggunakan cover placeholder default.")
                    blank_img = Image.new("RGB", (600, 600), color=(30, 30, 46))
                    blank_img.save(temp_cover, "JPEG", quality=90)

                if self.stop_requested:
                    break

                # 2. Download Semua Track Audio
                downloaded_track_files = []
                for t_idx, track_info in enumerate(tracks, start=1):
                    if self.stop_requested:
                        break

                    t_name = track_info["name"]
                    t_url = track_info["url"]
                    t_ref = track_info.get("referer", REFERER)
                    t_out_tmpl = os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}.%(ext)s")
                    t_final_mp3 = os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}.mp3")

                    temp_files.extend([
                        t_final_mp3,
                        os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}_.mp3"),
                        os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}.mp4"),
                        os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}.temp.mp4"),
                        os.path.join(temp_dir, f"temp_{rjid}_t{t_idx}.(ext)s.mp3"),
                    ])

                    t_start_ratio = 0.15 + 0.65 * ((t_idx - 1) / len(tracks))
                    t_end_ratio = 0.15 + 0.65 * (t_idx / len(tracks))

                    self._update_progress(
                        base_pct + item_step * t_start_ratio,
                        f"[{idx+1}/{total_items}] Menghubungkan {t_name} [{t_idx}/{len(tracks)}]...",
                        speed="Menghubungkan...",
                        eta="Menghitung...",
                        size_str="Ukuran: Memuat...",
                    )
                    self._log(f"[2/3] Mengunduh {t_name} [{t_idx}/{len(tracks)}]...")

                    conn_int = int(self.config.get("connections", 16))
                    conn_val = str(conn_int)
                    aria_x = min(conn_int, 16)
                    ytdlp_bin = get_bin_executable("yt-dlp")
                    aria2c_bin = get_bin_executable("aria2c")
                    ffmpeg_bin = get_bin_executable("ffmpeg")
                    ffmpeg_dir = os.path.dirname(os.path.abspath(ffmpeg_bin))

                    actual_file = None
                    max_track_attempts = 3
                    for attempt_idx in range(1, max_track_attempts + 1):
                        if self.stop_requested:
                            break

                        if attempt_idx > 1:
                            self._log(f"  [i] Mengulang pengunduhan {t_name} (Percobaan {attempt_idx}/{max_track_attempts})...")
                            time.sleep(2)

                        cmd_ytdlp = [
                            ytdlp_bin,
                            "--newline",
                            "--ffmpeg-location", ffmpeg_dir,
                            "--socket-timeout", "60",
                            "--retries", "10",
                            "--extractor-retries", "5",
                            "--fragment-retries", "10",
                            "--retry-sleep", "3",
                            "-N", conn_val,
                        ]
                        if os.path.exists(aria2c_bin):
                            cmd_ytdlp.extend([
                                "--downloader", "aria2c",
                                "--downloader", "dash,m3u8:native",
                                "--downloader-args", f"aria2c:-s {conn_val} -x {aria_x} -j {conn_val} -k 1M --file-allocation=none --summary-interval=1 --timeout=60 --max-tries=10 --retry-wait=3 --continue=true",
                            ])
                        else:
                            cmd_ytdlp.extend([
                                "--downloader", "dash,m3u8:native",
                            ])
                        cmd_ytdlp.extend([
                            "--fixup", "never",
                            "--add-header", f"Referer: {t_ref}",
                            "--add-header", f"Origin: {t_ref}",
                            "--add-header", "Accept-Language: zh-CN,zh;q=0.9,ja;q=0.8,en;q=0.7",
                            "--user-agent", USER_AGENT,
                            t_url,
                            "-o", t_out_tmpl,
                        ])
                        self.current_process = subprocess.Popen(
                            cmd_ytdlp,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1,
                            universal_newlines=True,
                            encoding="utf-8",
                            errors="replace",
                            env=os.environ.copy(),
                            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
                        )

                        # Baca stream output secara real-time untuk update indikator kecepatan, ETA, dan ukuran
                        if self.current_process.stdout:
                            for raw_line in iter(self.current_process.stdout.readline, ""):
                                if self.stop_requested:
                                    break
                                line_s = raw_line.strip()
                                if not line_s:
                                    continue

                                # 1. Parse format standar yt-dlp
                                m_yt = RE_YTDLP_PROGRESS.search(line_s)
                                if m_yt:
                                    pct_val = float(m_yt.group(1))
                                    total_sz = m_yt.group(2) or "-"
                                    sp = m_yt.group(3) or "-"
                                    et = m_yt.group(4) or "-"
                                    track_part = t_start_ratio + (t_end_ratio - t_start_ratio) * (pct_val / 100.0)
                                    cur_overall = base_pct + item_step * track_part
                                    frag_cur = m_yt.group(5)
                                    frag_tot = m_yt.group(6)
                                    frag_info = f" (Frag {frag_cur}/{frag_tot})" if frag_cur and frag_tot else ""
                                    self._update_progress(
                                        cur_overall,
                                        status_text=f"[{idx+1}/{total_items}] Mengunduh {t_name} [{t_idx}/{len(tracks)}]{frag_info}",
                                        speed=f"Kecepatan: {sp}",
                                        eta=f"Sisa Waktu: {et}",
                                        size_str=f"Total: ~{total_sz}",
                                    )
                                    continue

                                # 2. Parse format summary aria2c
                                m_ar = RE_ARIA2_PROGRESS.search(line_s)
                                if m_ar:
                                    cur_sz = m_ar.group(1)
                                    tot_sz = m_ar.group(2)
                                    pct_val = float(m_ar.group(3))
                                    sp = f"{m_ar.group(4)}/s"
                                    et = m_ar.group(5)
                                    track_part = t_start_ratio + (t_end_ratio - t_start_ratio) * (pct_val / 100.0)
                                    cur_overall = base_pct + item_step * track_part
                                    self._update_progress(
                                        cur_overall,
                                        status_text=f"[{idx+1}/{total_items}] Mengunduh {t_name} [{t_idx}/{len(tracks)}]",
                                        speed=f"Kecepatan: {sp}",
                                        eta=f"Sisa Waktu: {et}",
                                        size_str=f"Ukuran: {cur_sz} / {tot_sz}",
                                    )
                                    continue

                                # 3. Parse format fragment HLS
                                m_fr = RE_FRAG_PROGRESS.search(line_s)
                                if m_fr:
                                    cur_f = int(m_fr.group(1))
                                    tot_f = int(m_fr.group(2))
                                    if tot_f > 0:
                                        pct_val = (cur_f / tot_f) * 100.0
                                        track_part = t_start_ratio + (t_end_ratio - t_start_ratio) * (pct_val / 100.0)
                                        cur_overall = base_pct + item_step * track_part
                                        self._update_progress(
                                            cur_overall,
                                            status_text=f"[{idx+1}/{total_items}] Mengunduh {t_name} (Frag {cur_f}/{tot_f})",
                                            speed=None,
                                            eta=None,
                                            size_str=f"Segmen: {cur_f}/{tot_f}",
                                        )
                                        continue

                                # Filter log agar log konsol bersih dari noise [generic], [download], [#a1b2c3], [info], [hlsnative], aria2 summary
                                if line_s.startswith("ERROR:") or line_s.startswith("WARNING:"):
                                    self._log(f"  [!] {line_s}")
                                elif not any(line_s.startswith(pfx) for pfx in ["[download]", "[#", "[generic]", "[info]", "[hlsnative]", "[ExtractAudio]", "[Merger]", "Deleting original file", "***", "===", "---", "FILE:", "Download Results:", "Status Legend:"]):
                                    self._log(f"  {line_s}")

                        self.current_process.wait()

                        # Deteksi file audio yang berhasil dibuat (berbagai format audio asli)
                        prefix = f"temp_{rjid}_t{t_idx}."
                        candidates = [
                            os.path.join(temp_dir, f) for f in os.listdir(temp_dir)
                            if f.startswith(prefix) and not f.endswith((".part", ".temp", ".ytdl", ".aria2"))
                        ]
                        actual_file = next((f for f in candidates if os.path.isfile(f) and os.path.getsize(f) > 0), None)
                        if actual_file:
                            temp_files.append(actual_file)
                            break

                    if self.stop_requested:
                        break

                    if not actual_file:
                        raise FileNotFoundError(f"File audio untuk {t_name} gagal diunduh atau diekstrak.")
                    downloaded_track_files.append(actual_file)

                if self.stop_requested:
                    break

                # 3. Tentukan nama dan format file output akhir (Smart Native Container)
                if configured_fmt == "auto":
                    first_codec = get_audio_codec(downloaded_track_files[0]) if downloaded_track_files else ""
                    out_ext = ".m4a" if first_codec == "aac" else (".mp3" if first_codec == "mp3" else ".m4a")
                else:
                    out_ext = f".{configured_fmt}"
                final_output = os.path.join(download_dir, f"{base_fname}{out_ext}")

                # 3. Embed Cover Art, Metadata & Chapters ke format audio
                self._update_progress(base_pct + item_step * 0.90, f"[{idx+1}/{total_items}] Menyematkan cover & metadata...")
                if len(downloaded_track_files) > 1:
                    self._log(f"[3/3] Menggabungkan {len(downloaded_track_files)} track, menyematkan penanda bab & metadata...")
                else:
                    self._log(f"[3/3] Menyematkan cover art, penanda bab & metadata...")

                embed_cover_and_merge(
                    track_files=downloaded_track_files,
                    cover_path=temp_cover,
                    output_name=final_output,
                    track_names=track_names,
                    meta=item,
                    rj_id=rjid,
                    log_func=self._log,
                )

                if self.stop_requested:
                    break

                # Validasi ketat file output
                if not os.path.exists(final_output) or os.path.getsize(final_output) == 0:
                    raise RuntimeError(f"Gagal memproses file audio final: {os.path.basename(final_output)}")

                if self.stop_requested:
                    break

                # Simpan ke riwayat unduhan & cache cover art
                add_to_history(
                    rjid=rjid,
                    title=title,
                    cv=item.get("cv", "-"),
                    circle=item.get("circle", "-"),
                    genre=item.get("genre", "-"),
                    age_rating=item.get("age_rating", "-"),
                    cover_url=cover_url,
                    output_path=final_output,
                    temp_cover_path=temp_cover,
                )

                item["status"] = "Selesai"
                self.after(0, lambda i=idx: self.tree.set(str(i), "status", "Selesai"))
                self.after(0, self._load_history_view)
                self._update_progress(
                    (idx + 1) * item_step,
                    f"[{idx+1}/{total_items}] Selesai {rjid}",
                    speed="Kecepatan: -",
                    eta="Sisa Waktu: -",
                    size_str="Status: Selesai",
                )
                self._log(f"[OK] SUKSES: Tersimpan di {os.path.basename(final_output)}")
                norm_out = os.path.normcase(os.path.abspath(final_output))
                self._chapters_cache.pop(norm_out, None)
                self.after(0, self._refresh_playlist_view)

            except Exception as e:
                if self.stop_requested:
                    break
                item["status"] = "Error"
                self.after(0, lambda i=idx: self.tree.set(str(i), "status", "Error"))
                self._log(f"[X] Gagal memproses {rjid}: {e}")

            finally:
                for tf in temp_files:
                    if os.path.exists(tf):
                        try:
                            os.remove(tf)
                        except OSError:
                            pass

        self.is_downloading = False
        self.current_process = None
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

        if self.stop_requested:
            self._log("[!] Semua proses download telah dihentikan.")
            self._update_progress(
                0,
                "Download Dihentikan",
                speed="Kecepatan: -",
                eta="Sisa Waktu: -",
                size_str="Ukuran: - / -",
            )
            # Kembalikan item yang statusnya masih Downloading ke Pending
            for idx, item in enumerate(self.queue_items):
                if item["status"] == "Downloading":
                    item["status"] = "Pending"
                    self.after(0, lambda i=idx: self.tree.set(str(i), "status", "Pending"))
        else:
            self._update_progress(
                100,
                "Semua proses selesai (100%)",
                speed="Kecepatan: -",
                eta="Sisa Waktu: -",
                size_str="Ukuran: Selesai",
            )
            self._log("\n--- Semua proses download dalam antrean selesai ---")
            self.after(0, lambda: show_dark_info(self, "Selesai", "Semua proses unduhan dalam antrean telah selesai!"))
