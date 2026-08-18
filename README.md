# 🎧 JapaneseASMR Downloader & Cover Art Embedder

Downloader audio HLS/M3U8 & Direct MP3 otomatis dengan penyemat cover art thumbnail, metadata ID3 lengkap, dan antarmuka Desktop GUI + CLI yang intuitif.

---

## ✨ Fitur Utama

- 🖼️ **Aplikasi Desktop GUI (`gui.py`)**:
  - **Live Preview Cover Art**: Menampilkan gambar cover karya langsung di aplikasi.
  - **Smart Scraper DLsite**: Otomatis mengekstrak **Judul Asli**, **Pengisi Suara (Multi-CV)**, **Circle / Brand**, **Genre / Tag**, dan **Rating Usia (R18 / All-Ages)**.
  - **Dukungan Format Fleksibel**: Otomatis mendeteksi sumber audio baik via HLS Stream (`.m3u8`) maupun direct file (`.mp3`).
  - **Tab Riwayat Unduhan**: Menyimpan daftar semua karya yang pernah didownload beserta cover, tanggal, ukuran, dan status ketersediaan file.
  - **Offline Cover Cache**: Menyimpan thumbnail cover mini secara lokal di `.cache/covers/` sehingga riwayat dapat dimuat secara offline.
  - **Custom Download Directory**: Bebas memilih lokasi folder penyimpanan di mana saja melalui tombol *Ganti Folder* (tersimpan di `config.json`).
  - **Tabel Antrean Interaktif**: Memantau progres antrean unduhan secara multi-threading tanpa freeze.
- 🚀 **Download Paralel Cepat**: Menggunakan `yt-dlp` dengan akselerasi 16 koneksi paralel via `aria2c`.
- 🏷️ **Penyematan Metadata ID3 Lengkap**: Menyematkan cover thumbnail, judul, artist (CV), album (Circle), genre, dan comment rating ke file MP3 via `ffmpeg`.
- 🔢 **Otomatisasi Kode RJ**: Cukup masukkan kode produk (misal: `RJ01673437`, `RJ278932`, dll).
- 📦 **Batch Multi-Download**: Mendukung download banyak ID sekaligus dalam satu antrean.
- ⏭️ **Auto-Skip**: Otomatis melewati file yang sudah pernah diunduh sebelumnya.
- 🎨 **CLI Interaktif & Berwarna (`main.py`)**: Pilihan mode CLI yang cepat dan ringan dengan kode warna ANSI.

---

## 🛠️ Prasyarat (Dependencies)

Pastikan program-program berikut sudah terinstal di sistem Anda dan terdaftar di PATH:

1. **Python 3.8+**
2. **Pillow** (untuk GUI): `pip install Pillow`
3. **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**
4. **[aria2](https://github.com/aria2/aria2)** (`aria2c`)
5. **[ffmpeg](https://ffmpeg.org/)**

---

## 🚀 Cara Penggunaan

Cukup jalankan file utama:
```bash
python main.py
```

Pilih mode yang diinginkan:
```text
Silakan pilih mode yang ingin dijalankan:
  [1] Mode Desktop GUI (Preview Cover, Antrean, & Riwayat)
  [2] Mode Terminal CLI (Cepat & Ringan)
  [0] Keluar

Pilih mode [1/2] (Tekan Enter untuk GUI):
```

### Shortcut Flag (Opsional)
```bash
python main.py --gui   # Langsung membuka mode Desktop GUI
python main.py --cli   # Langsung membuka mode Terminal CLI
```

---

### Versi Windows Batch (`main.bat`)

Sebagai cadangan, Anda juga dapat menjalankan:
```cmd
.\main.bat
```

---

## 📁 Struktur Project

```text
japaneseasmr-dl/
├── config_manager.py  # Modul manajemen konfigurasi & riwayat unduhan
├── gui.py             # Aplikasi Desktop GUI (Dark Mode & Riwayat)
├── main.py            # Menu utama & Mode Terminal CLI
├── main.bat           # Script cadangan versi Windows Batch
├── README.md          # Dokumentasi project
└── downloads/         # Folder default penyimpanan file MP3
```

---

## 📄 Lisensi
[MIT License](LICENSE)
