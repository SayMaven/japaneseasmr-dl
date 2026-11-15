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
)
from dlsite_scraper import (
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
from ui.dialogs import show_dark_info
from ui.toast import show_toast


class DownloadWorkerMixin:
    """Mixin providing background download processing, real-time progress tracking, and graceful task cancellation."""
    def _update_progress(self, val_pct, status_text=None, speed=None, eta=None, size_str=None):
        def _apply():
            try:
                if not self.winfo_exists():
                    return
                clamped = max(0.0, min(100.0, float(val_pct)))
                if hasattr(self, "progress_bar") and self.progress_bar.winfo_exists():
                    if hasattr(self.progress_bar, "set"):
                        self.progress_bar.set(clamped / 100.0)
                    else:
                        self.progress_bar["value"] = clamped
                if hasattr(self, "lbl_progress_pct") and self.lbl_progress_pct.winfo_exists():
                    self.lbl_progress_pct.configure(text=f"{int(clamped)}%")
                if status_text and hasattr(self, "lbl_progress_status") and self.lbl_progress_status.winfo_exists():
                    self.lbl_progress_status.configure(text=f"Status: {status_text}")
                if speed is not None and hasattr(self, "lbl_progress_speed") and self.lbl_progress_speed.winfo_exists():
                    self.lbl_progress_speed.configure(text=speed)
                if eta is not None and hasattr(self, "lbl_progress_eta") and self.lbl_progress_eta.winfo_exists():
                    self.lbl_progress_eta.configure(text=eta)
                if size_str is not None and hasattr(self, "lbl_progress_size") and self.lbl_progress_size.winfo_exists():
                    self.lbl_progress_size.configure(text=size_str)
            except Exception:
                pass
        try:
            self.after(0, _apply)
        except Exception:
            pass

    def _start_download_thread(self):
        if self.is_downloading:
            return
        if not self.queue_items:
            show_dark_info(self, t("msg_info_title"), t("msg_queue_empty"))
            return

        self.is_downloading = True
        self.stop_requested = False
        if hasattr(self, "start_btn") and self.start_btn.winfo_exists():
            self.start_btn.configure(state="disabled")
        if hasattr(self, "stop_btn") and self.stop_btn.winfo_exists():
            self.stop_btn.configure(state="normal")

        threading.Thread(target=self._download_worker, daemon=True).start()

    def _stop_downloads(self):
        self.stop_requested = True
        self._log(t("log_stopping_download"))
        if hasattr(self, "stop_btn") and self.stop_btn.winfo_exists():
            self.stop_btn.configure(state="disabled")

        # 1. Terminate active subprocess and child processes (yt-dlp, aria2c, ffmpeg)
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

        # 2. Clean up any orphaned download or transcoding processes
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

        # 3. Clean up residual temporary files in .cache/temp/
        temp_dir = os.path.join(".cache", "temp")
        if os.path.exists(temp_dir):
            for fname in os.listdir(temp_dir):
                fpath = os.path.join(temp_dir, fname)
                try:
                    if os.path.isfile(fpath):
                        os.remove(fpath)
                except OSError:
                    pass

        self._update_progress(0, t("status_download_stopped"))

    def _download_worker(self):
        download_dir = get_download_dir()
        os.makedirs(download_dir, exist_ok=True)
        total_items = len(self.queue_items)
        self._update_progress(0, t("status_preparing_items", total=total_items))

        for idx, item in enumerate(self.queue_items):
            if self.stop_requested:
                break

            item_step = 100.0 / max(1, total_items)
            base_pct = idx * item_step

            if item["status"] == "Selesai":
                self._update_progress((idx + 1) * item_step, t("status_skipped_done", current=idx+1, total=total_items))
                continue

            rjid = item["rjid"]
            title = item.get("title", "")

            # Resolve destination filename and check for existing files
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
                self._log(t("log_file_already_exists", filename=os.path.basename(existing_file)))
                item["status"] = "Selesai"
                self.after(0, lambda i=idx: self.tree.set(str(i), "status", t("status_completed")))
                self._update_progress((idx + 1) * item_step, t("status_skipped_existing", current=idx+1, total=total_items))
                continue

            # Mark current item as active download
            item["status"] = "Downloading"
            self.after(0, lambda i=idx: self.tree.set(str(i), "status", t("status_downloading")))
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
                self._log(t("log_processing_item", current=idx+1, total=total_items, rjid=rjid))

                # 0. Discover all audio tracks (including multi-track, omake, or asmr.one fallback)
                self._update_progress(base_pct + item_step * 0.05, t("status_scanning_tracks", current=idx+1, total=total_items))
                self._log(t("log_detecting_tracks"))
                tracks = discover_all_audio_tracks(rjid, REFERER, USER_AGENT)
                track_names = [t["name"] for t in tracks]
                source_type = tracks[0].get("source", "japaneseasmr") if tracks else "japaneseasmr"
                if source_type == "asmr.one":
                    self._log(t("log_audio_source_asmrone"))
                else:
                    self._log(t("log_audio_source_primary"))

                if len(tracks) > 1:
                    self._log(t("log_tracks_detected_multiple", count=len(tracks), names=', '.join(track_names)))
                else:
                    self._log(t("log_tracks_detected_single"))

                if self.stop_requested:
                    break

                # 1. Download and standardize cover image as JPEG for shell preview compatibility
                self._update_progress(base_pct + item_step * 0.15, t("status_downloading_cover", current=idx+1, total=total_items))
                self._log(t("log_downloading_cover"))

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
                    self._log(t("log_cover_not_found_placeholder"))
                    blank_img = Image.new("RGB", (600, 600), color=(30, 30, 46))
                    blank_img.save(temp_cover, "JPEG", quality=90)

                if self.stop_requested:
                    break

                # 2. Download audio tracks sequentially
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
                        t("status_connecting_track", current=idx+1, total=total_items, name=t_name, t_idx=t_idx, total_tracks=len(tracks)),
                        speed=t("status_connecting"),
                        eta=t("status_calculating"),
                        size_str=t("status_size_label", size=t("status_loading")),
                    )
                    self._log(t("log_downloading_track", name=t_name, current=t_idx, total=len(tracks)))

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
                            self._log(t("log_retry_download_track", name=t_name, attempt=attempt_idx, max_attempts=max_track_attempts))
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

                        # Stream process output in real-time to extract progress, speed, ETA, and size metrics
                        if self.current_process.stdout:
                            for raw_line in iter(self.current_process.stdout.readline, ""):
                                if self.stop_requested:
                                    break
                                line_s = raw_line.strip()
                                if not line_s:
                                    continue

                                # 1. Parse standard yt-dlp progress output
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
                                        status_text=t("status_downloading_track_item", current=idx+1, total=total_items, name=t_name, t_idx=t_idx, total_tracks=len(tracks), frag_info=frag_info),
                                        speed=t("status_speed_label", speed=sp),
                                        eta=t("status_eta_label", eta=et),
                                        size_str=t("status_size_label", size=f"~{total_sz}"),
                                    )
                                    continue

                                # 2. Parse aria2c summary progress output
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
                                        status_text=t("status_downloading_track_item", current=idx+1, total=total_items, name=t_name, t_idx=t_idx, total_tracks=len(tracks), frag_info=""),
                                        speed=t("status_speed_label", speed=sp),
                                        eta=t("status_eta_label", eta=et),
                                        size_str=t("status_size_label", size=f"{cur_sz} / {tot_sz}"),
                                    )
                                    continue

                                # 3. Parse HLS fragment progress output
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
                                            status_text=t("status_downloading_track_item", current=idx+1, total=total_items, name=t_name, t_idx=t_idx, total_tracks=len(tracks), frag_info=f" (Frag {cur_f}/{tot_f})"),
                                            speed=None,
                                            eta=None,
                                            size_str=t("status_segment_label", cur=cur_f, total=tot_f),
                                        )
                                        continue

                                # Filter noisy CLI lines from log console to keep output readable
                                if line_s.startswith("ERROR:") or line_s.startswith("WARNING:"):
                                    self._log(f"  [!] {line_s}")
                                elif not any(line_s.startswith(pfx) for pfx in ["[download]", "[#", "[generic]", "[info]", "[hlsnative]", "[ExtractAudio]", "[Merger]", "Deleting original file", "***", "===", "---", "FILE:", "Download Results:", "Status Legend:"]):
                                    self._log(f"  {line_s}")

                        self.current_process.wait()

                        # Identify the downloaded audio candidate in the temporary directory
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

                # 3. Determine final container format and file path (Smart Native Container)
                if configured_fmt == "auto":
                    first_codec = get_audio_codec(downloaded_track_files[0]) if downloaded_track_files else ""
                    out_ext = ".m4a" if first_codec == "aac" else (".mp3" if first_codec == "mp3" else ".m4a")
                else:
                    out_ext = f".{configured_fmt}"
                final_output = os.path.join(download_dir, f"{base_fname}{out_ext}")

                # 4. Embed cover art, metadata tags, and chapter markers into audio container
                self._update_progress(base_pct + item_step * 0.90, t("status_embedding_metadata", current=idx+1, total=total_items))
                if len(downloaded_track_files) > 1:
                    self._log(t("log_merging_tracks_chapters", count=len(downloaded_track_files)))
                else:
                    self._log(t("log_embedding_cover_chapters"))

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

                # Verify that the output file exists and is non-empty
                if not os.path.exists(final_output) or os.path.getsize(final_output) == 0:
                    raise RuntimeError(f"Gagal memproses file audio final: {os.path.basename(final_output)}")

                if self.stop_requested:
                    break

                # Persist download metadata to history store and cover cache
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
                self.after(0, lambda i=idx: self.tree.set(str(i), "status", t("status_completed")))
                self.after(0, self._load_history_view)
                self._update_progress(
                    (idx + 1) * item_step,
                    t("status_completed_item", current=idx+1, total=total_items, rjid=rjid),
                    speed=t("status_speed_label", speed="-"),
                    eta=t("status_eta_label", eta="-"),
                    size_str=t("status_size_label", size=t("status_completed")),
                )
                self._log(t("log_success_saved", filename=os.path.basename(final_output)))
                norm_out = os.path.normcase(os.path.abspath(final_output))
                self._chapters_cache.pop(norm_out, None)
                self.after(0, self._refresh_playlist_view)

            except Exception as e:
                if self.stop_requested:
                    break
                item["status"] = "Error"
                self.after(0, lambda i=idx: self.tree.set(str(i), "status", t("status_error")))
                self._log(t("log_failed_processing", rjid=rjid, error=str(e)))

            finally:
                for tf in temp_files:
                    if os.path.exists(tf):
                        try:
                            os.remove(tf)
                        except OSError:
                            pass

        self.is_downloading = False
        self.current_process = None

        def _finish_buttons():
            try:
                if hasattr(self, "start_btn") and self.start_btn.winfo_exists():
                    self.start_btn.configure(state="normal")
                if hasattr(self, "stop_btn") and self.stop_btn.winfo_exists():
                    self.stop_btn.configure(state="disabled")
            except Exception:
                pass

        try:
            self.after(0, _finish_buttons)
        except Exception:
            pass

        if self.stop_requested:
            self._log(t("log_all_downloads_stopped"))
            self._update_progress(
                0,
                t("status_download_stopped"),
                speed=t("status_speed_label", speed="-"),
                eta=t("status_eta_label", eta="-"),
                size_str=t("status_size_label", size="- / -"),
            )
            # Revert items interrupted in downloading state back to Pending
            for idx, item in enumerate(self.queue_items):
                if item["status"] == "Downloading":
                    item["status"] = "Pending"
                    self.after(0, lambda i=idx: self.tree.set(str(i), "status", t("status_ready")))
        else:
            self._update_progress(
                100,
                t("status_all_finished_pct"),
                speed=t("status_speed_label", speed="-"),
                eta=t("status_eta_label", eta="-"),
                size_str=t("status_size_label", size=t("status_completed")),
            )
            self._log(t("log_all_downloads_completed"))
            if self.cfg.get("notify_popup", True):
                self.after(
                    0,
                    lambda: show_toast(
                        self,
                        title=t("msg_download_complete"),
                        message=t("msg_queue_finished"),
                        toast_type="success",
                        duration_ms=4500,
                    ),
                )
