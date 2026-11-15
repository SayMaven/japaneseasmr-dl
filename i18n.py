# -*- coding: utf-8 -*-
"""Internationalization (i18n) module for JapaneseASMR Downloader.

Supports 4 languages:
- English ('en')
- Bahasa Indonesia ('id')
- Japanese ('ja')
- Simplified Chinese ('zh')

Provides automatic Windows system UI language detection with fallback chains
and regional LCID primary language bitmasking.
"""

import ctypes
import locale
import os
import sys

from version import APP_VERSION

# In-memory cached active language to avoid repetitive disk I/O
_ACTIVE_LANG = None


class SafeDict(dict):
    """Safe dictionary for str.format_map that preserves missing keys rather than raising KeyError."""
    def __missing__(self, key):
        return f"{{{key}}}"


LANG_DEFINITIONS = {
    "auto": {
        "en": "System Default (Auto)",
        "id": "Sistem (Otomatis)",
        "ja": "システム言語 (自動)",
        "zh": "系统语言 (自动)",
    },
    "en": {"native": "English", "code": "en"},
    "id": {"native": "Bahasa Indonesia", "code": "id"},
    "ja": {"native": "日本語", "code": "ja"},
    "zh": {"native": "简体中文", "code": "zh"},
}

TRANSLATIONS = {
    # ========================== ENGLISH ==========================
    "en": {
        "nav_main_header": "MAIN NAVIGATION",
        "settings_subtitle": "Manage download preferences, audio format, cache maintenance, and core engine configuration.",
        "lbl_settings_automation": "Automation & Notification Preferences",
        "lbl_detailed_name_desc": "Use full folder name format including RJ code",
        "lbl_notify_popup_desc": "Show confirmation dialog when download successfully completes",
        "lbl_auto_clipboard_desc": "Automatically paste link when detecting DLsite URL in clipboard",
        "lbl_ytdlp_ver_installed": "Installed yt-dlp Version: {ver}",
        "lbl_ytdlp_ver_checking": "Checking...",
        "status_ytdlp_ready": "Ready to check for latest release",
        "status_ytdlp_updating": "Downloading latest release...",
        "status_ytdlp_latest": "Already on the latest version",
        "status_ytdlp_failed": "Update check failed",
        "lbl_maintenance_actions": "Maintenance Actions",
        "lbl_storage_statistics": "Storage Space Statistics",
        "lbl_stat_covers": "• Cover Thumbnail Cache: {count} files ({size})",
        "lbl_stat_temp": "• Temporary Files Cache: {count} files ({size})",
        "lbl_stat_hist": "• Total Download History: {count} entries",
        "msg_settings_saved": "Settings saved successfully!",
        "msg_settings_reset": "Form reset to saved settings",
        "btn_reset_form": "Reset Form",
        "btn_github_repo": "GitHub Repository",
        "btn_report_issues": "Report Issues",
        "about_app_desc": "Native downloader and audio player for Japanese ASMR works.\nEquipped with Windows Media Foundation playback engine, CUE chapter management, and modern Tokyo Night UI.",
        # App Info & Header
        "app_title": "JapaneseASMR Downloader & Audio Player",
        "app_version": "Version {ver} (Release Build) • Windows Edition",
        "nav_main_header": "MAIN NAVIGATION",
        "btn_change_dir": "Change Folder",
        "btn_open_folder": "Open Folder",
        "btn_settings": "Settings",
        "lbl_save_location": "Save Location: {path}",

        # Notebook Tabs
        "tab_queue": "Download Queue",
        "tab_history": "Download History",
        "tab_player": "Audio Player",

        # Queue Tab
        "lbl_input_group": "Download Input & Queue",
        "lbl_input_hint": "Enter RJ code, asmr.one / JapaneseASMR / DLsite URL:",
        "btn_paste": "Paste Clipboard",
        "btn_add_queue": "Add to Queue",
        "btn_clear_queue": "Clear",
        "btn_start_download": "Start Download",
        "btn_stop_download": "Stop Download",
        "lbl_log_header": "Processing Logs & Status Output",

        # Queue Table Columns
        "col_rjid": "RJ Code",
        "col_title": "Work Title",
        "col_status": "Status",
        "col_progress": "Progress",
        "col_speed": "Speed",
        "col_eta": "ETA",

        # Status Strings
        "status_ready": "Ready",
        "status_in_queue": "Queued",
        "status_fetching_meta": "Fetching metadata...",
        "status_downloading": "Downloading",
        "status_merging": "Merging & Tagging...",
        "status_completed": "Completed",
        "status_stopped": "Stopped",
        "status_error": "Failed",
        "status_all_done": "All downloads completed.",

        # Work Detail Panel (Right Side)
        "lbl_preview_title": "Work Details & Cover Art",
        "lbl_detail_rjid": "Work ID:",
        "lbl_detail_title": "Title:",
        "lbl_detail_cv": "Voice Actors (CV):",
        "lbl_detail_circle": "Circle / Maker:",
        "lbl_detail_age": "Age Rating:",
        "lbl_detail_genre": "Genre & Tags:",
        "val_none": "-",

        # History Tab
        "lbl_stat_total": "Total Works: {count}",
        "lbl_stat_size": "Disk Usage: {size}",
        "lbl_search_hint": "Search title, CV, Circle...",
        "btn_search": "Search",
        "btn_reset_search": "Reset",
        "btn_play_selected": "Play in Player",
        "btn_open_file_dir": "Show in Explorer",
        "btn_clear_history": "Clear History",
        "col_hist_rjid": "RJ Code",
        "col_hist_title": "Work Title",
        "col_hist_cv": "Voice Actor (CV)",
        "col_hist_circle": "Circle / Maker",
        "col_hist_date": "Downloaded Date",

        # Audio Player Tab
        "lbl_playlist": "Audio Collection",
        "lbl_chapters": "Chapters / Scenes",
        "btn_refresh_playlist": "Refresh List",
        "col_play_title": "Work Title / File",
        "col_play_duration": "Duration",
        "col_chap_time": "Time",
        "col_chap_title": "Chapter Title / Scene",
        "chk_loop": "Repeat Track",
        "lbl_volume": "Volume: {vol}%",
        "btn_play": "Play",
        "btn_pause": "Pause",
        "btn_stop": "Stop",
        "btn_prev": "Prev",
        "btn_next": "Next",

        # Settings Dialog
        "settings_title": "Settings - JapaneseASMR Downloader",
        "settings_header": "Application Settings",
        "lbl_category": "CATEGORIES",
        "tab_settings_general": "General",
        "tab_settings_download": "Download & Network",
        "tab_settings_cache": "Storage & Cache",
        "tab_settings_about": "About",

        "lbl_settings_general_title": "General Settings",
        "lbl_language": "Display Language:",
        "lbl_language_desc": "Select application language (Auto follows Windows language).",
        "lbl_download_dir": "Default Download Directory:",
        "lbl_storage_folder": "Default Download Directory",
        "lbl_storage_folder_desc": "Main directory for downloaded ASMR files and extracted tracks.",
        "btn_browse": "Browse...",
        "lbl_file_pref": "Download & File Preferences:",
        "chk_detailed_name": "Use work title as audio filename (uncheck for RJ code only)",
        "chk_notify": "Show popup notification when download completes",
        "chk_notify_popup": "Show popup notification when download completes",
        "chk_clipboard": "Auto-detect and paste RJ code when copying to clipboard",
        "chk_auto_clipboard": "Auto-detect and paste links when copying DLsite URLs",

        "lbl_settings_download_title": "Download Engine & Acceleration",
        "lbl_audio_format": "Target Audio Container & Codec:",
        "lbl_audio_format_desc": "Lossless instant remux with native chapter markers",
        "fmt_auto": "Auto (Recommended - M4A Fast Remux / MP3)",
        "fmt_m4a": "M4A (Apple AAC, Lossless Remux, Native Chapters)",
        "fmt_mp3": "MP3 (High Quality 320k + Companion CUE Sheet)",
        "fmt_flac": "FLAC (Lossless Studio Quality)",
        "fmt_wav": "WAV (Uncompressed PCM Audio)",
        "lbl_connections": "Parallel aria2c Connections (1 - 32):",
        "lbl_aria2_connections": "Parallel aria2c Connections (Multi-source)",
        "lbl_aria2_connections_desc": "Simultaneous connection threads used to accelerate downloads (4 - 32).",
        "lbl_ytdlp_engine": "yt-dlp Core Engine",
        "lbl_ytdlp_channel": "yt-dlp Update Channel:",
        "btn_update_ytdlp": "Check for yt-dlp Updates",

        "lbl_settings_cache_title": "Storage & Cache Management",
        "lbl_cache_summary": "Disk Cache & Temporary Storage",
        "lbl_cover_cache_size": "Cover Art Cache: {size}",
        "lbl_temp_cache_size": "Temporary Partitions: {size}",
        "btn_clear_covers": "Clear Cover Cache",
        "btn_clear_temp": "Clear Temporary Files",
        "btn_clear_all_history": "Clear All Download History",

        "lbl_settings_about_title": "About Application",
        "lbl_about_desc": "All-in-one desktop application to download JapaneseASMR audio, auto-merge multi-tracks & omake, embed HD cover art & official DLsite metadata, and enjoy built-in gapless audio playback.",
        "lbl_about_author": "Developer: SayMaven",
        "lbl_about_license": "License: GNU GPL v3.0",
        "btn_visit_github": "Visit GitHub Repository",

        "btn_save_settings": "Save Settings",
        "btn_cancel": "Cancel",
        "btn_ok": "OK",
        "btn_understand": "Understood",
        "btn_close": "Close",
        "btn_yes": "Yes",
        "btn_no": "No",
        "msg_settings_saved": "Settings saved successfully!",

        # Notifications & Confirmation Dialogs
        "msg_confirm_clear_history": "Are you sure you want to delete all download history?",
        "msg_confirm_clear_covers": "Are you sure you want to delete all cached cover images?",
        "msg_confirm_clear_temp": "Are you sure you want to delete all temporary files?",
        "msg_download_complete": "Download Completed!",
        "msg_queue_finished": "All download processes in the queue have completed!",
        "msg_download_success_detail": "Successfully downloaded and processed:\n{title}",
        "msg_error_title": "Error",
        "msg_info_title": "Information",
        "msg_no_item_selected": "Please select a work from the list first.",
        "msg_queue_empty": "Queue is empty. Enter an RJ code first.",
        "msg_already_downloading": "Download is already running in background.",

        # Console Logs & Dynamic Status Messages
        "log_stopping_download": "[!] Stopping download process immediately...",
        "log_file_already_exists": "[SKIP] File '{filename}' already exists.",
        "log_processing_item": "\n--- [{current}/{total}] Processing {rjid} ---",
        "log_detecting_tracks": "[0/3] Detecting audio track count...",
        "log_audio_source_asmrone": "[i] Audio source: asmr.one (Fallback active)",
        "log_audio_source_primary": "[i] Audio source: JapaneseASMR (Primary)",
        "log_tracks_detected_multiple": "[i] Detected {count} tracks ({names}). All tracks will be merged automatically!",
        "log_tracks_detected_single": "[i] Detected 1 audio track.",
        "log_downloading_cover": "[1/3] Downloading cover art...",
        "log_cover_not_found_placeholder": "[!] Online cover art not found, using default placeholder cover.",
        "log_downloading_track": "[2/3] Downloading {name} [{current}/{total}]...",
        "log_retry_download_track": "  [i] Retrying download of {name} (Attempt {attempt}/{max_attempts})...",
        "log_merging_tracks_chapters": "[3/3] Merging {count} tracks, embedding chapter markers & metadata...",
        "log_embedding_cover_chapters": "[3/3] Embedding cover art, chapter markers & metadata...",
        "log_success_saved": "[OK] SUCCESS: Saved to {filename}",
        "log_failed_processing": "[X] Failed to process {rjid}: {error}",
        "log_all_downloads_stopped": "[!] All download processes have been stopped.",
        "log_all_downloads_completed": "\n--- All queued downloads completed ---",
        "log_added_items_to_queue": "[+] Added {count} item(s) to queue.",
        "log_queue_cleared": "[i] Queue cleared.",
        "log_clipboard_read_failed": "[!] Failed to read clipboard: {error}",
        "log_history_entry_deleted": "[i] Deleted history entry for: {rjid}",
        "log_hybrid_chapter_mapped": "[✓] Hybrid Chapter: Primary track ({dur:.1f}s) successfully mapped into {count} chapter markers{extra}!",
        "log_asmrone_metadata_synced": "[✓] Verified: {count} physical tracks synchronized with asmr.one metadata!",
        "log_japaneseasmr_chapters_synced": "[✓] JapaneseASMR Tracklist: Successfully synchronized {count} chapter markers from japaneseasmr.com!",
        "log_embedding_chapters_into_file": "[i] Embedding {count} chapter markers into {filename}...",
        "log_audio_fast_remux": "[+] Packaging audio in original stream format (Instant Fast Remux)...",
        "log_adjusting_audio_format": "[!] Adjusting audio format...",
        "log_processing_audio_format": "[i] Processing audio format ({format})...",
        "log_cue_sheet_created": "[✓] CUE Sheet created for audio players (Foobar2000): {filename}",
        "status_preparing_items": "Preparing {total} items...",
        "status_skipped_existing": "[{current}/{total}] Completed (Already Exists)",
        "status_skipped_done": "[{current}/{total}] Completed (Skipped)",
        "status_scanning_tracks": "[{current}/{total}] Scanning audio tracks...",
        "status_downloading_cover": "[{current}/{total}] Downloading cover art...",
        "status_connecting_track": "[{current}/{total}] Connecting to {name} [{t_idx}/{total_tracks}]...",
        "status_downloading_track_item": "[{current}/{total}] Downloading {name} [{t_idx}/{total_tracks}]{frag_info}",
        "status_embedding_metadata": "[{current}/{total}] Embedding cover & metadata...",
        "status_completed_item": "[{current}/{total}] Completed {rjid}",
        "status_download_stopped": "Download Stopped",
        "status_all_finished_pct": "All processes completed (100%)",
        "status_connecting": "Connecting...",
        "status_calculating": "Calculating...",
        "status_loading": "Loading...",
        "status_speed_label": "Speed: {speed}",
        "status_eta_label": "ETA: {eta}",
        "status_size_label": "Size: {size}",
        "status_segment_label": "Segments: {cur}/{total}",
    },

    # ========================== INDONESIAN ==========================
    "id": {
        "nav_main_header": "NAVIGASI UTAMA",
        "settings_subtitle": "Kelola preferensi unduhan, format audio, pemeliharaan cache, dan konfigurasi engine.",
        "lbl_settings_automation": "Preferensi Otomatisasi & Notifikasi",
        "lbl_detailed_name_desc": "Gunakan format nama folder lengkap beserta kode RJ",
        "lbl_notify_popup_desc": "Tampilkan dialog konfirmasi saat unduhan berhasil selesai",
        "lbl_auto_clipboard_desc": "Otomatis paste tautan saat mendeteksi URL DLsite di clipboard",
        "lbl_ytdlp_ver_installed": "Versi yt-dlp Terpasang: {ver}",
        "lbl_ytdlp_ver_checking": "Memeriksa...",
        "status_ytdlp_ready": "Siap memeriksa rilis terbaru",
        "status_ytdlp_updating": "Sedang mengunduh rilis terbaru...",
        "status_ytdlp_latest": "Sudah versi terbaru",
        "status_ytdlp_failed": "Pembaruan gagal",
        "lbl_maintenance_actions": "Tindakan Pemeliharaan",
        "lbl_storage_statistics": "Statistik Ruang Penyimpanan",
        "lbl_stat_covers": "• Cache Thumbnail Cover: {count} file ({size})",
        "lbl_stat_temp": "• Cache Berkas Sementara: {count} file ({size})",
        "lbl_stat_hist": "• Total Riwayat Unduhan: {count} entri",
        "msg_settings_saved": "Pengaturan berhasil disimpan!",
        "msg_settings_reset": "Form dikembalikan ke pengaturan tersimpan",
        "btn_reset_form": "Reset Form",
        "btn_github_repo": "Repositori GitHub",
        "btn_report_issues": "Lapor Masalah (Issues)",
        "about_app_desc": "Aplikasi utilitas pengunduh dan pemutar audio native untuk karya suara ASMR Jepang.\nDilengkapi Windows Media Foundation playback engine, manajemen CUE chapter, dan Tokyo Night UI modern.",
        # App Info & Header
        "app_title": "JapaneseASMR Downloader & Audio Player",
        "app_version": "Versi {ver} (Release Build) • Windows Edition",
        "btn_change_dir": "Ganti Folder",
        "btn_open_folder": "Buka Folder",
        "btn_settings": "Pengaturan",
        "lbl_save_location": "Lokasi Simpan: {path}",

        # Notebook Tabs
        "tab_queue": "Antrean Download",
        "tab_history": "Riwayat Unduhan",
        "tab_player": "Pemutar Audio",

        # Queue Tab
        "lbl_input_group": "Input & Antrean Unduhan",
        "lbl_input_hint": "Masukkan kode RJ, tautan asmr.one / JapaneseASMR / DLsite:",
        "btn_paste": "Tempel Clipboard",
        "btn_add_queue": "Tambah Antrean",
        "btn_clear_queue": "Kosongkan",
        "btn_start_download": "Mulai Unduh",
        "btn_stop_download": "Hentikan Unduh",
        "lbl_log_header": "Log Pemrosesan & Status Unduhan",

        # Queue Table Columns
        "col_rjid": "Kode RJ",
        "col_title": "Judul Karya",
        "col_status": "Status",
        "col_progress": "Kemajuan",
        "col_speed": "Kecepatan",
        "col_eta": "Sisa Waktu",

        # Status Strings
        "status_ready": "Siap",
        "status_in_queue": "Dalam Antrean",
        "status_fetching_meta": "Mengambil info...",
        "status_downloading": "Mengunduh",
        "status_merging": "Menggabungkan & Tagging...",
        "status_completed": "Selesai",
        "status_stopped": "Dihentikan",
        "status_error": "Gagal",
        "status_all_done": "Semua unduhan selesai.",

        # Work Detail Panel (Right Side)
        "lbl_preview_title": "Pratinjau Karya & Metadata",
        "lbl_detail_rjid": "Kode RJ:",
        "lbl_detail_title": "Judul:",
        "lbl_detail_cv": "Pengisi Suara (CV):",
        "lbl_detail_circle": "Lingkar Karya (Circle):",
        "lbl_detail_age": "Batasan Usia:",
        "lbl_detail_genre": "Genre & Tag:",
        "val_none": "-",

        # History Tab
        "lbl_stat_total": "Total Karya: {count}",
        "lbl_stat_size": "Ukuran di Disk: {size}",
        "lbl_search_hint": "Cari judul, CV, Circle...",
        "btn_search": "Cari",
        "btn_reset_search": "Reset",
        "btn_play_selected": "Putar di Player",
        "btn_open_file_dir": "Buka di Explorer",
        "btn_clear_history": "Hapus Riwayat",
        "col_hist_rjid": "Kode RJ",
        "col_hist_title": "Judul Karya",
        "col_hist_cv": "Pengisi Suara (CV)",
        "col_hist_circle": "Lingkar Karya (Circle)",
        "col_hist_date": "Tanggal Unduh",

        # Audio Player Tab
        "lbl_playlist": "Daftar Koleksi Audio",
        "lbl_chapters": "Daftar Bab & Adegan",
        "btn_refresh_playlist": "Segarkan Daftar",
        "col_play_title": "Judul Karya / File",
        "col_play_duration": "Durasi",
        "col_chap_time": "Waktu",
        "col_chap_title": "Judul Bab / Scene",
        "chk_loop": "Putar Berulang",
        "lbl_volume": "Volume: {vol}%",
        "btn_play": "Putar",
        "btn_pause": "Jeda",
        "btn_stop": "Berhenti",
        "btn_prev": "Sebelumnya",
        "btn_next": "Berikutnya",

        # Settings Dialog
        "settings_title": "Pengaturan - JapaneseASMR Downloader",
        "settings_header": "Pengaturan Aplikasi",
        "lbl_category": "KATEGORI",
        "tab_settings_general": "Umum",
        "tab_settings_download": "Unduhan & Jaringan",
        "tab_settings_cache": "Penyimpanan & Cache",
        "tab_settings_about": "Tentang Aplikasi",

        "lbl_settings_general_title": "Pengaturan Umum",
        "lbl_language": "Bahasa Tampilan:",
        "lbl_language_desc": "Pilih bahasa antarmuka (Otomatis mengikuti bahasa Windows).",
        "lbl_download_dir": "Lokasi Folder Penyimpanan Download:",
        "lbl_storage_folder": "Lokasi Folder Penyimpanan Download",
        "lbl_storage_folder_desc": "Direktori utama penyimpanan berkas audio ASMR dan track yang diekstrak.",
        "btn_browse": "Browse...",
        "lbl_file_pref": "Preferensi & Perilaku Unduhan:",
        "chk_detailed_name": "Gunakan judul karya sebagai nama file audio (hilangkan centang untuk hanya kode RJ)",
        "chk_notify": "Tampilkan notifikasi popup saat unduhan selesai",
        "chk_notify_popup": "Tampilkan notifikasi popup saat unduhan selesai",
        "chk_clipboard": "Otomatis deteksi dan tempel kode RJ saat menyalin ke clipboard",
        "chk_auto_clipboard": "Otomatis paste tautan saat mendeteksi URL DLsite di clipboard",

        "lbl_settings_download_title": "Engine Unduhan & Akselerasi",
        "lbl_audio_format": "Format Kontainer Audio Target:",
        "lbl_audio_format_desc": "Remux lossless instan dengan penanda bab native",
        "fmt_auto": "Otomatis (Rekomendasi - M4A Fast Remux / MP3)",
        "fmt_m4a": "M4A (Apple AAC, Lossless Remux, Bab Native)",
        "fmt_mp3": "MP3 (Kualitas Tinggi 320k + Berkas CUE Sheet)",
        "fmt_flac": "FLAC (Kualitas Studio Lossless)",
        "fmt_wav": "WAV (Audio PCM Tanpa Kompresi)",
        "lbl_connections": "Jumlah Koneksi Paralel aria2c (1 - 32):",
        "lbl_aria2_connections": "Koneksi Paralel aria2c (Multi-source)",
        "lbl_aria2_connections_desc": "Jumlah koneksi thread simultan untuk mempercepat proses unduhan (4 - 32).",
        "lbl_ytdlp_engine": "Engine Inti yt-dlp",
        "lbl_ytdlp_channel": "Channel Pembaruan yt-dlp:",
        "btn_update_ytdlp": "Periksa Pembaruan yt-dlp",

        "lbl_settings_cache_title": "Manajemen Penyimpanan & Cache",
        "lbl_cache_summary": "Penyimpanan Cache & File Partisi Sementara",
        "lbl_cover_cache_size": "Cache Gambar Cover: {size}",
        "lbl_temp_cache_size": "File Partisi Sementara: {size}",
        "btn_clear_covers": "Bersihkan Cache Cover",
        "btn_clear_temp": "Bersihkan File Sementara",
        "btn_clear_all_history": "Hapus Semua Riwayat Unduhan",

        "lbl_settings_about_title": "Tentang Aplikasi",
        "lbl_about_desc": "Aplikasi desktop all-in-one modern untuk mengunduh audio JapaneseASMR, menggabungkan multi-track & omake, menyematkan cover art HD & metadata DLsite resmi, serta dilengkapi pemutar audio bawaan.",
        "lbl_about_author": "Pengembang: SayMaven",
        "lbl_about_license": "Lisensi: GNU GPL v3.0",
        "btn_visit_github": "Kunjungi Repositori GitHub",

        "btn_save_settings": "Simpan Pengaturan",
        "btn_cancel": "Batal",
        "btn_ok": "OK",
        "btn_understand": "Mengerti",
        "btn_close": "Tutup",
        "btn_yes": "Ya",
        "btn_no": "Tidak",
        "msg_settings_saved": "Pengaturan berhasil disimpan!",

        # Notifications & Confirmation Dialogs
        "msg_confirm_clear_history": "Apakah Anda yakin ingin menghapus seluruh riwayat unduhan?",
        "msg_confirm_clear_covers": "Apakah Anda yakin ingin menghapus seluruh cache gambar cover?",
        "msg_confirm_clear_temp": "Apakah Anda yakin ingin membersihkan semua file sementara?",
        "msg_download_complete": "Unduhan Selesai!",
        "msg_queue_finished": "Semua proses unduhan dalam antrean telah selesai!",
        "msg_download_success_detail": "Berhasil mengunduh dan memproses:\n{title}",
        "msg_error_title": "Terjadi Kesalahan",
        "msg_info_title": "Pemberitahuan",
        "msg_no_item_selected": "Silakan pilih karya dari daftar terlebih dahulu.",
        "msg_queue_empty": "Antrean kosong. Masukkan kode RJ terlebih dahulu.",
        "msg_already_downloading": "Proses unduhan masih berlangsung di latar belakang.",

        # Console Logs & Dynamic Status Messages
        "log_stopping_download": "[!] Menghentikan proses download seketika...",
        "log_file_already_exists": "[SKIP] File '{filename}' sudah ada.",
        "log_processing_item": "\n--- [{current}/{total}] Memproses {rjid} ---",
        "log_detecting_tracks": "[0/3] Mendeteksi jumlah track audio...",
        "log_audio_source_asmrone": "[i] Sumber audio: asmrone (Fallback aktif)",
        "log_audio_source_primary": "[i] Sumber audio: JapaneseASMR (Utama)",
        "log_tracks_detected_multiple": "[i] Terdeteksi {count} track ({names}). Semua akan digabung otomatis!",
        "log_tracks_detected_single": "[i] Terdeteksi 1 track audio.",
        "log_downloading_cover": "[1/3] Mengunduh cover art...",
        "log_cover_not_found_placeholder": "[!] Cover art online tidak ditemukan, menggunakan cover placeholder default.",
        "log_downloading_track": "[2/3] Mengunduh {name} [{current}/{total}]...",
        "log_retry_download_track": "  [i] Mengulang pengunduhan {name} (Percobaan {attempt}/{max_attempts})...",
        "log_merging_tracks_chapters": "[3/3] Menggabungkan {count} track, menyematkan penanda bab & metadata...",
        "log_embedding_cover_chapters": "[3/3] Menyematkan cover art, penanda bab & metadata...",
        "log_success_saved": "[OK] SUKSES: Tersimpan di {filename}",
        "log_failed_processing": "[X] Gagal memproses {rjid}: {error}",
        "log_all_downloads_stopped": "[!] Semua proses download telah dihentikan.",
        "log_all_downloads_completed": "\n--- Semua proses download dalam antrean selesai ---",
        "log_added_items_to_queue": "[+] Menambahkan {count} item ke antrean.",
        "log_queue_cleared": "[i] Antrean dibersihkan.",
        "log_clipboard_read_failed": "[!] Gagal membaca clipboard: {error}",
        "log_history_entry_deleted": "[i] Menghapus riwayat untuk: {rjid}",
        "log_hybrid_chapter_mapped": "[✓] Hybrid Chapter: Track utama ({dur:.1f}s) berhasil dipetakan menjadi {count} bab cerita{extra}!",
        "log_asmrone_metadata_synced": "[✓] Terverifikasi: {count} track fisik disinkronkan dengan metadata asmr.one!",
        "log_japaneseasmr_chapters_synced": "[✓] Tracklist JapaneseASMR: Berhasil menyinkronkan {count} bab cerita dari situs japaneseasmr.com!",
        "log_embedding_chapters_into_file": "[i] Menyematkan {count} penanda bab (chapters) ke dalam {filename}...",
        "log_audio_fast_remux": "[+] Mengemas audio sesuai format asli (Fast Remux instan)...",
        "log_adjusting_audio_format": "[!] Menyesuaikan format audio...",
        "log_processing_audio_format": "[i] Memproses format audio ({format})...",
        "log_cue_sheet_created": "[✓] CUE Sheet dibuat untuk pemutar audio (Foobar2000): {filename}",
        "status_preparing_items": "Mempersiapkan {total} item...",
        "status_skipped_existing": "[{current}/{total}] Selesai (Sudah Ada)",
        "status_skipped_done": "[{current}/{total}] Selesai (Dilewati)",
        "status_scanning_tracks": "[{current}/{total}] Memindai track audio...",
        "status_downloading_cover": "[{current}/{total}] Mengunduh cover art...",
        "status_connecting_track": "[{current}/{total}] Menghubungkan {name} [{t_idx}/{total_tracks}]...",
        "status_downloading_track_item": "[{current}/{total}] Mengunduh {name} [{t_idx}/{total_tracks}]{frag_info}",
        "status_embedding_metadata": "[{current}/{total}] Menyematkan cover & metadata...",
        "status_completed_item": "[{current}/{total}] Selesai {rjid}",
        "status_download_stopped": "Download Dihentikan",
        "status_all_finished_pct": "Semua proses selesai (100%)",
        "status_connecting": "Menghubungkan...",
        "status_calculating": "Menghitung...",
        "status_loading": "Memuat...",
        "status_speed_label": "Kecepatan: {speed}",
        "status_eta_label": "Sisa Waktu: {eta}",
        "status_size_label": "Ukuran: {size}",
        "status_segment_label": "Segmen: {cur}/{total}",
    },

    # ========================== JAPANESE ==========================
    "ja": {
        "nav_main_header": "メインナビゲーション",
        "settings_subtitle": "ダウンロード設定、音声フォーマット、キャッシュ管理、コアエンジンの構成を管理します。",
        "lbl_settings_automation": "自動化と通知の設定",
        "lbl_detailed_name_desc": "RJコードを含む完全なフォルダ名形式を使用する",
        "lbl_notify_popup_desc": "ダウンロード完了時に確認ダイアログを表示する",
        "lbl_auto_clipboard_desc": "クリップボードのDLsite URLを自動検出して貼り付ける",
        "lbl_ytdlp_ver_installed": "インストール済み yt-dlp バージョン: {ver}",
        "lbl_ytdlp_ver_checking": "確認中...",
        "status_ytdlp_ready": "最新リリースの確認準備完了",
        "status_ytdlp_updating": "最新リリースをダウンロード中...",
        "status_ytdlp_latest": "すでに最新バージョンです",
        "status_ytdlp_failed": "更新の確認に失敗しました",
        "lbl_maintenance_actions": "メンテナンス操作",
        "lbl_storage_statistics": "ストレージ容量統計",
        "lbl_stat_covers": "• カバー画像キャッシュ: {count} 件 ({size})",
        "lbl_stat_temp": "• 一時ファイルキャッシュ: {count} 件 ({size})",
        "lbl_stat_hist": "• ダウンロード履歴合計: {count} 件",
        "msg_settings_saved": "設定が正常に保存されました！",
        "msg_settings_reset": "保存された設定にリセットしました",
        "btn_reset_form": "リセット",
        "btn_github_repo": "GitHub リポジトリ",
        "btn_report_issues": "問題を報告 (Issues)",
        "about_app_desc": "日本のASMR作品向けネイティブダウンローダー＆オーディオプレイヤー。\nWindows Media Foundation再生エンジン、CUEチャプター管理、モダンなTokyo Night UIを搭載。",
        # App Info & Header
        "app_title": "JapaneseASMR Downloader & Audio Player",
        "app_version": "バージョン {ver} (Release Build) • Windows Edition",
        "btn_change_dir": "フォルダ変更",
        "btn_open_folder": "フォルダを開く",
        "btn_settings": "設定",
        "lbl_save_location": "保存先: {path}",

        # Notebook Tabs
        "tab_queue": "ダウンロードキュー",
        "tab_history": "ダウンロード履歴",
        "tab_player": "オーディオプレーヤー",

        # Queue Tab
        "lbl_input_group": "入力とダウンロードキュー",
        "lbl_input_hint": "RJ番号、asmr.one / JapaneseASMR / DLsite のURLを入力:",
        "btn_paste": "クリップボード貼付",
        "btn_add_queue": "キューに追加",
        "btn_clear_queue": "クリア",
        "btn_start_download": "ダウンロード開始",
        "btn_stop_download": "ダウンロード停止",
        "lbl_log_header": "処理ログとステータス出力",

        # Queue Table Columns
        "col_rjid": "RJ番号",
        "col_title": "作品名",
        "col_status": "状態",
        "col_progress": "進捗",
        "col_speed": "速度",
        "col_eta": "残り時間",

        # Status Strings
        "status_ready": "準備完了",
        "status_in_queue": "キュー待機中",
        "status_fetching_meta": "メタデータ取得中...",
        "status_downloading": "ダウンロード中",
        "status_merging": "結合およびタグ付け中...",
        "status_completed": "完了",
        "status_stopped": "停止",
        "status_error": "エラー",
        "status_all_done": "すべてのダウンロードが完了しました。",

        # Work Detail Panel (Right Side)
        "lbl_preview_title": "作品詳細・カバーアート",
        "lbl_detail_rjid": "作品ID:",
        "lbl_detail_title": "タイトル:",
        "lbl_detail_cv": "声優 (CV):",
        "lbl_detail_circle": "サークル名:",
        "lbl_detail_age": "年齢指定:",
        "lbl_detail_genre": "ジャンル・タグ:",
        "val_none": "-",

        # History Tab
        "lbl_stat_total": "総作品数: {count}",
        "lbl_stat_size": "ディスク容量: {size}",
        "lbl_search_hint": "作品名、声優、サークルを検索...",
        "btn_search": "検索",
        "btn_reset_search": "リセット",
        "btn_play_selected": "プレーヤーで再生",
        "btn_open_file_dir": "エクスプローラーで表示",
        "btn_clear_history": "履歴を消去",
        "col_hist_rjid": "RJ番号",
        "col_hist_title": "作品名",
        "col_hist_cv": "声優 (CV)",
        "col_hist_circle": "サークル名",
        "col_hist_date": "ダウンロード日時",

        # Audio Player Tab
        "lbl_playlist": "オーディオコレクション",
        "lbl_chapters": "チャプター / シーン一覧",
        "btn_refresh_playlist": "リスト更新",
        "col_play_title": "トラック名 / ファイル",
        "col_play_duration": "時間",
        "col_chap_time": "開始",
        "col_chap_title": "チャプター名 / シーン",
        "chk_loop": "リピート再生",
        "lbl_volume": "音量: {vol}%",
        "btn_play": "再生",
        "btn_pause": "一時停止",
        "btn_stop": "停止",
        "btn_prev": "前へ",
        "btn_next": "次へ",

        # Settings Dialog
        "settings_title": "設定 - JapaneseASMR Downloader",
        "settings_header": "アプリケーション設定",
        "lbl_category": "カテゴリー",
        "tab_settings_general": "一般",
        "tab_settings_download": "ダウンロードとネットワーク",
        "tab_settings_cache": "ストレージとキャッシュ",
        "tab_settings_about": "バージョン情報",

        "lbl_settings_general_title": "一般設定",
        "lbl_language": "表示言語:",
        "lbl_language_desc": "インターフェース言語を選択（自動選択はWindowsの言語に追従）。",
        "lbl_download_dir": "デフォルトのダウンロード先フォルダ:",
        "lbl_storage_folder": "ダウンロード保存先フォルダ",
        "lbl_storage_folder_desc": "ダウンロードしたASMR音声と展開トラックの保存場所。",
        "btn_browse": "参照...",
        "lbl_file_pref": "ダウンロードとファイル設定:",
        "chk_detailed_name": "作品名を音声ファイル名に使用（チェックを外すとRJ番号のみ）",
        "chk_notify": "ダウンロード完了時にポップアップ通知を表示する",
        "chk_notify_popup": "ダウンロード完了時にポップアップ通知を表示する",
        "chk_clipboard": "クリップボードのRJ番号を自動検出して貼り付ける",
        "chk_auto_clipboard": "クリップボードのDLsite URLを自動検出して貼り付ける",

        "lbl_settings_download_title": "ダウンロードエンジンとアクセラレーション",
        "lbl_audio_format": "出力音声フォーマット:",
        "lbl_audio_format_desc": "高速ロスレスリマックス（チャプター保持）",
        "fmt_auto": "自動（推奨 - M4A 高速リマックス / MP3）",
        "fmt_m4a": "M4A（Apple AAC、ロスレス、チャプター埋め込み）",
        "fmt_mp3": "MP3（高品質 320k + CUEシート付属）",
        "fmt_flac": "FLAC（スタジオ音質・完全可逆圧縮）",
        "fmt_wav": "WAV（非圧縮 PCM オーディオ）",
        "lbl_connections": "aria2c 並列接続数 (1 - 32):",
        "lbl_aria2_connections": "aria2c 並列接続数（マルチスレッド）",
        "lbl_aria2_connections_desc": "ダウンロードを高速化するための同時接続スレッド数 (4 - 32)。",
        "lbl_ytdlp_engine": "yt-dlp コアエンジン",
        "lbl_ytdlp_channel": "yt-dlp 更新チャンネル:",
        "btn_update_ytdlp": "yt-dlp の更新を確認",

        "lbl_settings_cache_title": "ストレージとキャッシュ管理",
        "lbl_cache_summary": "キャッシュと一時ファイル",
        "lbl_cover_cache_size": "カバー画像キャッシュ: {size}",
        "lbl_temp_cache_size": "一時ファイル容量: {size}",
        "btn_clear_covers": "カバーキャッシュを消去",
        "btn_clear_temp": "一時ファイルを消去",
        "btn_clear_all_history": "すべてのダウンロード履歴を消去",

        "lbl_settings_about_title": "このアプリについて",
        "lbl_about_desc": "JapaneseASMR音声をダウンロードし、マルチトラックや特典音声を自動結合、公式DLsiteのHDカバーとメタデータを埋め込み、内蔵プレーヤーで楽しめるオールインワンアプリです。",
        "lbl_about_author": "開発者: SayMaven",
        "lbl_about_license": "ライセンス: GNU GPL v3.0",
        "btn_visit_github": "GitHub リポジトリを開く",

        "btn_save_settings": "設定を保存",
        "btn_cancel": "キャンセル",
        "btn_ok": "OK",
        "btn_understand": "了解",
        "btn_close": "閉じる",
        "btn_yes": "はい",
        "btn_no": "いいえ",
        "msg_settings_saved": "設定を保存しました！",

        # Notifications & Confirmation Dialogs
        "msg_confirm_clear_history": "すべてのダウンロード履歴を消去してもよろしいですか？",
        "msg_confirm_clear_covers": "すべてのカバー画像キャッシュを削除してもよろしいですか？",
        "msg_confirm_clear_temp": "すべての一時ファイルを削除してもよろしいですか？",
        "msg_download_complete": "ダウンロード完了！",
        "msg_queue_finished": "キュー内のすべてのダウンロードが完了しました！",
        "msg_download_success_detail": "ダウンロードと処理が完了しました:\n{title}",
        "msg_error_title": "エラー",
        "msg_info_title": "お知らせ",
        "msg_no_item_selected": "リストから作品を選択してください。",
        "msg_queue_empty": "キューが空です。RJ番号を入力してください。",
        "msg_already_downloading": "ダウンロードはバックグラウンドですでに実行中です。",

        # Console Logs & Dynamic Status Messages
        "log_stopping_download": "[!] ダウンロード処理を直ちに停止しています...",
        "log_file_already_exists": "[スキップ] ファイル '{filename}' は既に存在します。",
        "log_processing_item": "\n--- [{current}/{total}] {rjid} を処理中 ---",
        "log_detecting_tracks": "[0/3] 音声トラック数を検出中...",
        "log_audio_source_asmrone": "[i] 音声ソース: asmr.one (フォールバック有効)",
        "log_audio_source_primary": "[i] 音声ソース: JapaneseASMR (プライマリ)",
        "log_tracks_detected_multiple": "[i] {count} 個のトラックを検出 ({names})。すべて自動で結合されます！",
        "log_tracks_detected_single": "[i] 1 個の音声トラックを検出しました。",
        "log_downloading_cover": "[1/3] カバー画像をダウンロード中...",
        "log_cover_not_found_placeholder": "[!] オンラインのカバー画像が見つかりません。デフォルトのプレースホルダーを使用します。",
        "log_downloading_track": "[2/3] {name} をダウンロード中 [{current}/{total}]...",
        "log_retry_download_track": "  [i] {name} のダウンロードを再試行中 (試行 {attempt}/{max_attempts})...",
        "log_merging_tracks_chapters": "[3/3] {count} 個のトラックを結合し、チャプターマーカーとメタデータを埋め込み中...",
        "log_embedding_cover_chapters": "[3/3] カバー画像、チャプターマーカー、メタデータを埋め込み中...",
        "log_success_saved": "[OK] 成功: {filename} に保存されました",
        "log_failed_processing": "[X] {rjid} の処理に失敗しました: {error}",
        "log_all_downloads_stopped": "[!] すべてのダウンロード処理が停止されました。",
        "log_all_downloads_completed": "\n--- キュー内のすべてのダウンロードが完了しました ---",
        "log_added_items_to_queue": "[+] キューに {count} 件のアイテムを追加しました。",
        "log_queue_cleared": "[i] キューをクリアしました。",
        "log_clipboard_read_failed": "[!] クリップボードの読み取りに失敗しました: {error}",
        "log_history_entry_deleted": "[i] 履歴を削除しました: {rjid}",
        "log_hybrid_chapter_mapped": "[✓] ハイブリッドチャプター: メイントラック ({dur:.1f}秒) が {count} 個のチャプターに正常にマッピングされました{extra}！",
        "log_asmrone_metadata_synced": "[✓] 検証済み: {count} 個の物理トラックが asmr.one のメタデータと同期されました！",
        "log_japaneseasmr_chapters_synced": "[✓] JapaneseASMR トラックリスト: japaneseasmr.com から {count} 個のチャプターが正常に同期されました！",
        "log_embedding_chapters_into_file": "[i] {count} 個のチャプターマーカーを {filename} に埋め込み中...",
        "log_audio_fast_remux": "[+] 元の形式で音声をパッケージ化中 (即時 Fast Remux)...",
        "log_adjusting_audio_format": "[!] 音声形式を調整中...",
        "log_processing_audio_format": "[i] 音声形式を処理中 ({format})...",
        "log_cue_sheet_created": "[✓] 音楽プレーヤー (Foobar2000) 用の CUE シートが作成されました: {filename}",
        "status_preparing_items": "{total} 件のアイテムを準備中...",
        "status_skipped_existing": "[{current}/{total}] 完了 (既に存在)",
        "status_skipped_done": "[{current}/{total}] 完了 (スキップ)",
        "status_scanning_tracks": "[{current}/{total}] 音声トラックをスキャン中...",
        "status_downloading_cover": "[{current}/{total}] カバー画像をダウンロード中...",
        "status_connecting_track": "[{current}/{total}] {name} に接続中 [{t_idx}/{total_tracks}]...",
        "status_downloading_track_item": "[{current}/{total}] {name} をダウンロード中 [{t_idx}/{total_tracks}]{frag_info}",
        "status_embedding_metadata": "[{current}/{total}] カバーとメタデータを埋め込み中...",
        "status_completed_item": "[{current}/{total}] 完了 {rjid}",
        "status_download_stopped": "ダウンロード停止",
        "status_all_finished_pct": "すべての処理が完了しました (100%)",
        "status_connecting": "接続中...",
        "status_calculating": "計算中...",
        "status_loading": "読み込み中...",
        "status_speed_label": "速度: {speed}",
        "status_eta_label": "残り時間: {eta}",
        "status_size_label": "サイズ: {size}",
        "status_segment_label": "セグメント: {cur}/{total}",
    },

    # ========================== CHINESE (SIMPLIFIED) ==========================
    "zh": {
        "nav_main_header": "主要导航",
        "settings_subtitle": "管理下载偏好、音频格式、缓存维护和核心引擎配置。",
        "lbl_settings_automation": "自动化与通知偏好",
        "lbl_detailed_name_desc": "使用包含RJ号的完整文件夹命名格式",
        "lbl_notify_popup_desc": "下载完成时显示确认弹窗",
        "lbl_auto_clipboard_desc": "检测到剪贴板中的DLsite链接时自动粘贴",
        "lbl_ytdlp_ver_installed": "已安装 yt-dlp 版本: {ver}",
        "lbl_ytdlp_ver_checking": "正在检查...",
        "status_ytdlp_ready": "随时可检查最新版本",
        "status_ytdlp_updating": "正在下载最新版本...",
        "status_ytdlp_latest": "已是最新版本",
        "status_ytdlp_failed": "检查更新失败",
        "lbl_maintenance_actions": "维护操作",
        "lbl_storage_statistics": "存储空间统计",
        "lbl_stat_covers": "• 封面缩略图缓存: {count} 个文件 ({size})",
        "lbl_stat_temp": "• 临时分段文件缓存: {count} 个文件 ({size})",
        "lbl_stat_hist": "• 下载历史总计: {count} 条记录",
        "msg_settings_saved": "设置已成功保存！",
        "msg_settings_reset": "已恢复为保存的设置",
        "btn_reset_form": "重置表单",
        "btn_github_repo": "GitHub 仓库",
        "btn_report_issues": "反馈问题 (Issues)",
        "about_app_desc": "面向日本ASMR作品的原生下载与音频播放工具。\n内置 Windows Media Foundation 播放引擎、CUE 分卷章节管理与现代化 Tokyo Night 主题界面。",
        # App Info & Header
        "app_title": "JapaneseASMR Downloader & Audio Player",
        "app_version": "版本 {ver} (Release Build) • Windows Edition",
        "btn_change_dir": "更改目录",
        "btn_open_folder": "打开目录",
        "btn_settings": "设置",
        "lbl_save_location": "保存位置: {path}",

        # Notebook Tabs
        "tab_queue": "下载队列",
        "tab_history": "下载历史",
        "tab_player": "音频播放器",

        # Queue Tab
        "lbl_input_group": "输入与下载队列",
        "lbl_input_hint": "输入RJ号、asmr.one / JapaneseASMR / DLsite 链接:",
        "btn_paste": "粘贴剪贴板",
        "btn_add_queue": "添加至队列",
        "btn_clear_queue": "清空",
        "btn_start_download": "开始下载",
        "btn_stop_download": "停止下载",
        "lbl_log_header": "处理日志与状态输出",

        # Queue Table Columns
        "col_rjid": "RJ号",
        "col_title": "作品标题",
        "col_status": "状态",
        "col_progress": "进度",
        "col_speed": "速度",
        "col_eta": "剩余时间",

        # Status Strings
        "status_ready": "就绪",
        "status_in_queue": "排队中",
        "status_fetching_meta": "获取元数据中...",
        "status_downloading": "正在下载",
        "status_merging": "合并与嵌入标签中...",
        "status_completed": "已完成",
        "status_stopped": "已停止",
        "status_error": "失败",
        "status_all_done": "所有下载已完成。",

        # Work Detail Panel (Right Side)
        "lbl_preview_title": "作品详情与封面",
        "lbl_detail_rjid": "作品ID:",
        "lbl_detail_title": "标题:",
        "lbl_detail_cv": "声优 (CV):",
        "lbl_detail_circle": "社团 / 制作社:",
        "lbl_detail_age": "年龄限制:",
        "lbl_detail_genre": "分类与标签:",
        "val_none": "-",

        # History Tab
        "lbl_stat_total": "作品总数: {count}",
        "lbl_stat_size": "占用空间: {size}",
        "lbl_search_hint": "搜索标题、声优、社团...",
        "btn_search": "搜索",
        "btn_reset_search": "重置",
        "btn_play_selected": "在播放器中播放",
        "btn_open_file_dir": "在文件管理器中显示",
        "btn_clear_history": "清空历史",
        "col_hist_rjid": "RJ号",
        "col_hist_title": "作品标题",
        "col_hist_cv": "声优 (CV)",
        "col_hist_circle": "社团 / 制作社",
        "col_hist_date": "下载日期",

        # Audio Player Tab
        "lbl_playlist": "音频收藏列表",
        "lbl_chapters": "章节与场景",
        "btn_refresh_playlist": "刷新列表",
        "col_play_title": "曲目名称 / 文件",
        "col_play_duration": "时长",
        "col_chap_time": "时间",
        "col_chap_title": "章节标题 / 场景",
        "chk_loop": "循环播放",
        "lbl_volume": "音量: {vol}%",
        "btn_play": "播放",
        "btn_pause": "暂停",
        "btn_stop": "停止",
        "btn_prev": "上一首",
        "btn_next": "下一首",

        # Settings Dialog
        "settings_title": "设置 - JapaneseASMR Downloader",
        "settings_header": "应用程序设置",
        "lbl_category": "类别",
        "tab_settings_general": "常规",
        "tab_settings_download": "下载与网络",
        "tab_settings_cache": "存储与缓存",
        "tab_settings_about": "关于",

        "lbl_settings_general_title": "常规设置",
        "lbl_language": "显示语言:",
        "lbl_language_desc": "选择界面语言（自动跟随Windows系统语言）。",
        "lbl_download_dir": "默认下载目录:",
        "lbl_storage_folder": "默认下载存储目录",
        "lbl_storage_folder_desc": "下载的ASMR音频与解压音轨的主要保存位置。",
        "btn_browse": "浏览...",
        "lbl_file_pref": "下载与文件偏好:",
        "chk_detailed_name": "使用作品标题作为音频文件名（取消勾选则仅使用RJ号）",
        "chk_notify": "下载完成时显示弹窗通知",
        "chk_notify_popup": "下载完成时显示弹窗通知",
        "chk_clipboard": "复制到剪贴板时自动检测并粘贴RJ号",
        "chk_auto_clipboard": "剪贴板检测到DLsite链接时自动粘贴",

        "lbl_settings_download_title": "下载引擎与加速",
        "lbl_audio_format": "目标音频格式:",
        "lbl_audio_format_desc": "快速无损重新封装（保留章节标记）",
        "fmt_auto": "自动（推荐 - M4A 快速封装 / MP3）",
        "fmt_m4a": "M4A（Apple AAC、无损封装、内置章节）",
        "fmt_mp3": "MP3（高音质 320k + 附带CUE分轨文件）",
        "fmt_flac": "FLAC（无损工作室音质）",
        "fmt_wav": "WAV（原始未压缩 PCM 音频）",
        "lbl_connections": "aria2c 并行连接数 (1 - 32):",
        "lbl_aria2_connections": "aria2c 并行连接数 (多线程加速)",
        "lbl_aria2_connections_desc": "用于多线程加速下载的同时并发连接数 (4 - 32)。",
        "lbl_ytdlp_engine": "yt-dlp 核心引擎",
        "lbl_ytdlp_channel": "yt-dlp 更新通道:",
        "btn_update_ytdlp": "检查 yt-dlp 更新",

        "lbl_settings_cache_title": "存储与缓存管理",
        "lbl_cache_summary": "磁盘缓存与临时存储",
        "lbl_cover_cache_size": "封面图片缓存: {size}",
        "lbl_temp_cache_size": "临时分段文件: {size}",
        "btn_clear_covers": "清理封面缓存",
        "btn_clear_temp": "清理临时文件",
        "btn_clear_all_history": "清空所有下载历史记录",

        "lbl_settings_about_title": "关于本应用",
        "lbl_about_desc": "一站式桌面应用，用于下载JapaneseASMR音频、自动合并多音轨与特典、嵌入DLsite官方高清封面与完整元数据，并配备内置音频播放器。",
        "lbl_about_author": "开发者: SayMaven",
        "lbl_about_license": "许可证: GNU GPL v3.0",
        "btn_visit_github": "访问 GitHub 仓库",

        "btn_save_settings": "保存设置",
        "btn_cancel": "取消",
        "btn_ok": "确定",
        "btn_understand": "知道了",
        "btn_close": "关闭",
        "btn_yes": "是",
        "btn_no": "否",
        "msg_settings_saved": "设置已成功保存！",

        # Notifications & Confirmation Dialogs
        "msg_confirm_clear_history": "确定要清空所有下载历史记录吗？",
        "msg_confirm_clear_covers": "确定要删除所有缓存的封面图片吗？",
        "msg_confirm_clear_temp": "确定要清理所有临时文件吗？",
        "msg_download_complete": "下载完成！",
        "msg_queue_finished": "队列中的所有下载任务已全部完成！",
        "msg_download_success_detail": "已成功下载并处理:\n{title}",
        "msg_error_title": "发生错误",
        "msg_info_title": "通知",
        "msg_no_item_selected": "请先从列表中选择一部作品。",
        "msg_queue_empty": "队列为空。请先输入RJ号。",
        "msg_already_downloading": "下载任务已在后台运行中。",

        # Console Logs & Dynamic Status Messages
        "log_stopping_download": "[!] 正在立即停止下载进程...",
        "log_file_already_exists": "[跳过] 文件 '{filename}' 已存在。",
        "log_processing_item": "\n--- [{current}/{total}] 正在处理 {rjid} ---",
        "log_detecting_tracks": "[0/3] 正在检测音轨数量...",
        "log_audio_source_asmrone": "[i] 音频源: asmr.one (备用源生效)",
        "log_audio_source_primary": "[i] 音频源: JapaneseASMR (主要源)",
        "log_tracks_detected_multiple": "[i] 检测到 {count} 个音轨 ({names})。将自动合并所有音轨！",
        "log_tracks_detected_single": "[i] 检测到 1 个音轨。",
        "log_downloading_cover": "[1/3] 正在下载封面图片...",
        "log_cover_not_found_placeholder": "[!] 未找到在线封面，使用默认占位封面。",
        "log_downloading_track": "[2/3] 正在下载 {name} [{current}/{total}]...",
        "log_retry_download_track": "  [i] 正在重试下载 {name} (第 {attempt}/{max_attempts} 次尝试)...",
        "log_merging_tracks_chapters": "[3/3] 正在合并 {count} 个音轨并嵌入章节标记和元数据...",
        "log_embedding_cover_chapters": "[3/3] 正在嵌入封面、章节标记和元数据...",
        "log_success_saved": "[OK] 成功: 已保存至 {filename}",
        "log_failed_processing": "[X] 处理 {rjid} 失败: {error}",
        "log_all_downloads_stopped": "[!] 所有下载进程已停止。",
        "log_all_downloads_completed": "\n--- 队列中的所有下载已完成 ---",
        "log_added_items_to_queue": "[+] 已添加 {count} 个项目至队列。",
        "log_queue_cleared": "[i] 队列已清空。",
        "log_clipboard_read_failed": "[!] 读取剪贴板失败: {error}",
        "log_history_entry_deleted": "[i] 已删除历史记录: {rjid}",
        "log_hybrid_chapter_mapped": "[✓] 混合章节: 主音轨 ({dur:.1f}秒) 成功映射为 {count} 个章节标记{extra}！",
        "log_asmrone_metadata_synced": "[✓] 已验证: {count} 个物理音轨已与 asmr.one 元数据同步！",
        "log_japaneseasmr_chapters_synced": "[✓] JapaneseASMR 曲目列表: 成功从 japaneseasmr.com 同步了 {count} 个章节标记！",
        "log_embedding_chapters_into_file": "[i] 正在将 {count} 个章节标记嵌入至 {filename}...",
        "log_audio_fast_remux": "[+] 正在按原始格式封装音频 (即时快速重新封装)...",
        "log_adjusting_audio_format": "[!] 正在调整音频格式...",
        "log_processing_audio_format": "[i] 正在处理音频格式 ({format})...",
        "log_cue_sheet_created": "[✓] 已为音频播放器 (Foobar2000) 创建 CUE 配置文件: {filename}",
        "status_preparing_items": "正在准备 {total} 个项目...",
        "status_skipped_existing": "[{current}/{total}] 已完成 (文件已存在)",
        "status_skipped_done": "[{current}/{total}] 已完成 (已跳过)",
        "status_scanning_tracks": "[{current}/{total}] 正在扫描音轨...",
        "status_downloading_cover": "[{current}/{total}] 正在下载封面图片...",
        "status_connecting_track": "[{current}/{total}] 正在连接 {name} [{t_idx}/{total_tracks}]...",
        "status_downloading_track_item": "[{current}/{total}] 正在下载 {name} [{t_idx}/{total_tracks}]{frag_info}",
        "status_embedding_metadata": "[{current}/{total}] 正在嵌入封面和元数据...",
        "status_completed_item": "[{current}/{total}] 已完成 {rjid}",
        "status_download_stopped": "下载已停止",
        "status_all_finished_pct": "所有任务处理完成 (100%)",
        "status_connecting": "正在连接...",
        "status_calculating": "正在计算...",
        "status_loading": "正在加载...",
        "status_speed_label": "速度: {speed}",
        "status_eta_label": "剩余时间: {eta}",
        "status_size_label": "大小: {size}",
        "status_segment_label": "分段: {cur}/{total}",
    },
}


def detect_windows_language():
    """Detect the user's Windows system UI language using Win32 Primary LCID bitmasking.
    
    Returns one of: 'id', 'ja', 'zh', or 'en'.
    """
    # 1. Try Win32 GetUserDefaultUILanguage
    try:
        if sys.platform == "win32":
            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            primary_lang = lcid & 0xFF
            if primary_lang == 0x21:  # Indonesian
                return "id"
            if primary_lang == 0x11:  # Japanese
                return "ja"
            if primary_lang == 0x04:  # Chinese (PRC, Taiwan, Hong Kong, Singapore, Macau)
                return "zh"
            if primary_lang == 0x09:  # English (US, UK, Australia, Canada, etc.)
                return "en"
    except Exception:
        pass

    # 2. Try default locale
    try:
        loc = locale.getdefaultlocale()[0]
        if loc:
            loc_lower = loc.lower()
            if loc_lower.startswith("id") or "indonesia" in loc_lower:
                return "id"
            if loc_lower.startswith("ja") or "japan" in loc_lower:
                return "ja"
            if loc_lower.startswith("zh") or "chinese" in loc_lower:
                return "zh"
            if loc_lower.startswith("en"):
                return "en"
    except Exception:
        pass

    # 3. Try standard environment variables (LANG, LC_ALL, LC_MESSAGES)
    for env_var in ("LANG", "LC_ALL", "LC_MESSAGES"):
        val = os.environ.get(env_var, "").lower()
        if val.startswith("id"):
            return "id"
        if val.startswith("ja"):
            return "ja"
        if val.startswith("zh"):
            return "zh"
        if val.startswith("en"):
            return "en"

    return "en"


def resolve_language(lang_code):
    """Resolve a language code. If set to 'auto', detects the Windows system UI language."""
    if not lang_code or lang_code == "auto":
        return detect_windows_language()
    code = str(lang_code).lower()
    if code in TRANSLATIONS:
        return code
    return "en"


def get_active_language():
    """Retrieve the currently active language code from memory."""
    global _ACTIVE_LANG
    if _ACTIVE_LANG is None:
        try:
            from config_manager import load_config
            cfg = load_config()
            configured = cfg.get("language", "auto")
            _ACTIVE_LANG = resolve_language(configured)
        except Exception:
            _ACTIVE_LANG = detect_windows_language()
    return _ACTIVE_LANG


def set_active_language(lang_code):
    """Set the active language code in memory."""
    global _ACTIVE_LANG
    _ACTIVE_LANG = resolve_language(lang_code)
    return _ACTIVE_LANG


def t(key, **kwargs):
    """Retrieve the localized string for a given translation key in the active language.
    
    Uses SafeDict to avoid KeyError exceptions if placeholders are missing.
    Automatically provides common global variables like 'ver' (APP_VERSION).
    """
    lang = get_active_language()
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    template = lang_dict.get(key)
    if template is None:
        # Fallback to English if the key is missing from the active language
        template = TRANSLATIONS["en"].get(key, key)

    if isinstance(template, str):
        format_kwargs = {"ver": APP_VERSION}
        if kwargs:
            format_kwargs.update(kwargs)
        try:
            return template.format_map(SafeDict(format_kwargs))
        except Exception:
            return template
    return template


def get_available_languages():
    """Return a list of (code, display_name) tuples for language selection dropdowns."""
    current_lang = get_active_language()
    auto_label = LANG_DEFINITIONS["auto"].get(current_lang, LANG_DEFINITIONS["auto"]["en"])
    return [
        ("auto", f"{auto_label}"),
        ("en", "English"),
        ("id", "Bahasa Indonesia"),
        ("ja", "日本語"),
        ("zh", "简体中文"),
    ]


def verify_all_translations():
    """Verify translation completeness across all supported languages against the English reference."""
    en_keys = set(TRANSLATIONS["en"].keys())
    missing_report = {}
    for lang in ("id", "ja", "zh"):
        lang_keys = set(TRANSLATIONS[lang].keys())
        missing = en_keys - lang_keys
        extra = lang_keys - en_keys
        if missing or extra:
            missing_report[lang] = {"missing": missing, "extra": extra}
    if missing_report:
        raise ValueError(f"Ditemukan ketidakkonsistenan translasi: {missing_report}")
    return True
