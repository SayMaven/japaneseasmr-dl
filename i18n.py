# -*- coding: utf-8 -*-
"""Modul Internasionalisasi (i18n) untuk JapaneseASMR Downloader.

Mendukung 4 bahasa:
- English ('en')
- Bahasa Indonesia ('id')
- 日本語 / Japanese ('ja')
- 简体中文 / Simplified Chinese ('zh')

Mendukung deteksi otomatis bahasa sistem Windows dengan fallback berantai dan
penanganan variasi LCID regional.
"""

import ctypes
import locale
import os
import sys

# Cache bahasa aktif dalam memori agar tidak membaca disk berulang-ulang
_ACTIVE_LANG = None


class SafeDict(dict):
    """Kamus aman untuk str.format_map agar tidak melempar KeyError jika ada key hilang."""
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
        # App Info & Header
        "app_title": "JapaneseASMR Downloader & Audio Player",
        "app_version": "Version 1.1.1 (Release Build) • Windows Edition",
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
        "btn_browse": "Browse...",
        "lbl_file_pref": "Download & File Preferences:",
        "chk_detailed_name": "Use work title as audio filename (uncheck for RJ code only)",
        "chk_notify": "Show popup notification when download completes",
        "chk_clipboard": "Auto-detect and paste RJ code when copying to clipboard",

        "lbl_settings_download_title": "Download Engine & Acceleration",
        "lbl_audio_format": "Target Audio Container & Codec:",
        "lbl_audio_format_desc": "Lossless instant remux with native chapter markers",
        "fmt_auto": "Auto (Recommended - M4A Fast Remux / MP3)",
        "fmt_m4a": "M4A (Apple AAC, Lossless Remux, Native Chapters)",
        "fmt_mp3": "MP3 (High Quality 320k + Companion CUE Sheet)",
        "lbl_connections": "Parallel aria2c Connections (1 - 32):",
        "lbl_ytdlp_channel": "yt-dlp Update Channel:",
        "btn_update_ytdlp": "Check for yt-dlp Updates",

        "lbl_settings_cache_title": "Storage & Cache Management",
        "lbl_cache_summary": "Disk Cache & Temporary Storage",
        "lbl_cover_cache_size": "Cover Art Cache: {size}",
        "lbl_temp_cache_size": "Temporary Partitions: {size}",
        "btn_clear_covers": "Clear Cover Cache",
        "btn_clear_temp": "Clear Temporary Files",

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
        "msg_download_success_detail": "Successfully downloaded and processed:\n{title}",
        "msg_error_title": "Error",
        "msg_info_title": "Information",
        "msg_no_item_selected": "Please select a work from the list first.",
        "msg_queue_empty": "Queue is empty. Enter an RJ code first.",
        "msg_already_downloading": "Download is already running in background.",
    },

    # ========================== INDONESIAN ==========================
    "id": {
        # App Info & Header
        "app_title": "JapaneseASMR Downloader & Audio Player",
        "app_version": "Versi 1.1.1 (Release Build) • Windows Edition",
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
        "btn_browse": "Browse...",
        "lbl_file_pref": "Preferensi & Perilaku Unduhan:",
        "chk_detailed_name": "Gunakan judul karya sebagai nama file audio (hilangkan centang untuk hanya kode RJ)",
        "chk_notify": "Tampilkan notifikasi popup saat unduhan selesai",
        "chk_clipboard": "Otomatis deteksi dan tempel kode RJ saat menyalin ke clipboard",

        "lbl_settings_download_title": "Engine Unduhan & Akselerasi",
        "lbl_audio_format": "Format Kontainer Audio Target:",
        "lbl_audio_format_desc": "Remux lossless instan dengan penanda bab native",
        "fmt_auto": "Otomatis (Rekomendasi - M4A Fast Remux / MP3)",
        "fmt_m4a": "M4A (Apple AAC, Lossless Remux, Bab Native)",
        "fmt_mp3": "MP3 (Kualitas Tinggi 320k + Berkas CUE Sheet)",
        "lbl_connections": "Jumlah Koneksi Paralel aria2c (1 - 32):",
        "lbl_ytdlp_channel": "Channel Pembaruan yt-dlp:",
        "btn_update_ytdlp": "Periksa Pembaruan yt-dlp",

        "lbl_settings_cache_title": "Manajemen Penyimpanan & Cache",
        "lbl_cache_summary": "Penyimpanan Cache & File Partisi Sementara",
        "lbl_cover_cache_size": "Cache Gambar Cover: {size}",
        "lbl_temp_cache_size": "File Partisi Sementara: {size}",
        "btn_clear_covers": "Bersihkan Cache Cover",
        "btn_clear_temp": "Bersihkan File Sementara",

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
        "msg_download_success_detail": "Berhasil mengunduh dan memproses:\n{title}",
        "msg_error_title": "Terjadi Kesalahan",
        "msg_info_title": "Pemberitahuan",
        "msg_no_item_selected": "Silakan pilih karya dari daftar terlebih dahulu.",
        "msg_queue_empty": "Antrean kosong. Masukkan kode RJ terlebih dahulu.",
        "msg_already_downloading": "Proses unduhan masih berlangsung di latar belakang.",
    },

    # ========================== JAPANESE ==========================
    "ja": {
        # App Info & Header
        "app_title": "JapaneseASMR Downloader & Audio Player",
        "app_version": "バージョン 1.1.1 (Release Build) • Windows Edition",
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
        "btn_browse": "参照...",
        "lbl_file_pref": "ダウンロードとファイル設定:",
        "chk_detailed_name": "作品名を音声ファイル名に使用（チェックを外すとRJ番号のみ）",
        "chk_notify": "ダウンロード完了時にポップアップ通知を表示する",
        "chk_clipboard": "クリップボードのRJ番号を自動検出して貼り付ける",

        "lbl_settings_download_title": "ダウンロードエンジンとアクセラレーション",
        "lbl_audio_format": "出力音声フォーマット:",
        "lbl_audio_format_desc": "高速ロスレスリマックス（チャプター保持）",
        "fmt_auto": "自動（推奨 - M4A 高速リマックス / MP3）",
        "fmt_m4a": "M4A（Apple AAC、ロスレス、チャプター埋め込み）",
        "fmt_mp3": "MP3（高品質 320k + CUEシート付属）",
        "lbl_connections": "aria2c 並列接続数 (1 - 32):",
        "lbl_ytdlp_channel": "yt-dlp 更新チャンネル:",
        "btn_update_ytdlp": "yt-dlp の更新を確認",

        "lbl_settings_cache_title": "ストレージとキャッシュ管理",
        "lbl_cache_summary": "キャッシュと一時ファイル",
        "lbl_cover_cache_size": "カバー画像キャッシュ: {size}",
        "lbl_temp_cache_size": "一時ファイル容量: {size}",
        "btn_clear_covers": "カバーキャッシュを消去",
        "btn_clear_temp": "一時ファイルを消去",

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
        "msg_download_success_detail": "ダウンロードと処理が完了しました:\n{title}",
        "msg_error_title": "エラー",
        "msg_info_title": "お知らせ",
        "msg_no_item_selected": "リストから作品を選択してください。",
        "msg_queue_empty": "キューが空です。RJ番号を入力してください。",
        "msg_already_downloading": "ダウンロードはバックグラウンドですでに実行中です。",
    },

    # ========================== CHINESE (SIMPLIFIED) ==========================
    "zh": {
        # App Info & Header
        "app_title": "JapaneseASMR Downloader & Audio Player",
        "app_version": "版本 1.1.1 (Release Build) • Windows Edition",
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
        "btn_browse": "浏览...",
        "lbl_file_pref": "下载与文件偏好:",
        "chk_detailed_name": "使用作品标题作为音频文件名（取消勾选则仅使用RJ号）",
        "chk_notify": "下载完成时显示弹窗通知",
        "chk_clipboard": "复制到剪贴板时自动检测并粘贴RJ号",

        "lbl_settings_download_title": "下载引擎与加速",
        "lbl_audio_format": "目标音频格式:",
        "lbl_audio_format_desc": "快速无损重新封装（保留章节标记）",
        "fmt_auto": "自动（推荐 - M4A 快速封装 / MP3）",
        "fmt_m4a": "M4A（Apple AAC、无损封装、内置章节）",
        "fmt_mp3": "MP3（高音质 320k + 附带CUE分轨文件）",
        "lbl_connections": "aria2c 并行连接数 (1 - 32):",
        "lbl_ytdlp_channel": "yt-dlp 更新通道:",
        "btn_update_ytdlp": "检查 yt-dlp 更新",

        "lbl_settings_cache_title": "存储与缓存管理",
        "lbl_cache_summary": "磁盘缓存与临时存储",
        "lbl_cover_cache_size": "封面图片缓存: {size}",
        "lbl_temp_cache_size": "临时分段文件: {size}",
        "btn_clear_covers": "清理封面缓存",
        "btn_clear_temp": "清理临时文件",

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
        "msg_download_success_detail": "已成功下载并处理:\n{title}",
        "msg_error_title": "发生错误",
        "msg_info_title": "通知",
        "msg_no_item_selected": "请先从列表中选择一部作品。",
        "msg_queue_empty": "队列为空。请先输入RJ号。",
        "msg_already_downloading": "下载任务已在后台运行中。",
    },
}


def detect_windows_language():
    """Mendeteksi bahasa Windows pengguna menggunakan Win32 Primary LCID bitmasking.
    
    Mengembalikan salah satu dari: 'id', 'ja', 'zh', atau 'en'.
    """
    # 1. Coba Win32 GetUserDefaultUILanguage
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

    # 2. Coba locale default
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

    # 3. Coba Environment variables (LANG, LC_ALL)
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
    """Menyelesaikan kode bahasa. Jika 'auto', mendeteksi bahasa sistem."""
    if not lang_code or lang_code == "auto":
        return detect_windows_language()
    code = str(lang_code).lower()
    if code in TRANSLATIONS:
        return code
    return "en"


def get_active_language():
    """Mengembalikan bahasa yang saat ini aktif dalam memori."""
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
    """Mengatur bahasa aktif dalam memori."""
    global _ACTIVE_LANG
    _ACTIVE_LANG = resolve_language(lang_code)
    return _ACTIVE_LANG


def t(key, **kwargs):
    """Mengambil string terjemahan untuk key tertentu dalam bahasa aktif.
    
    Menggunakan SafeDict agar tidak melempar KeyError jika ada placeholder yang hilang.
    """
    lang = get_active_language()
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    template = lang_dict.get(key)
    if template is None:
        # Fallback ke bahasa Inggris jika key tidak ditemukan di bahasa aktif
        template = TRANSLATIONS["en"].get(key, key)

    if kwargs and isinstance(template, str):
        try:
            return template.format_map(SafeDict(kwargs))
        except Exception:
            return template
    return template


def get_available_languages():
    """Mengembalikan list tuple (code, display_name) untuk combobox pengaturan."""
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
    """Uji verifikasi otomatis kelengkapan kunci terjemahan di semua bahasa."""
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
