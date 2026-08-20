# JapaneseASMR Downloader & Audio Player

Aplikasi desktop *all-in-one* modern untuk mengunduh audio JapaneseASMR, menggabungkan *multi-track* & bonus/omake secara otomatis, menyematkan *cover art* HD & metadata DLsite resmi ke dalam tag ID3 MP3, serta dilengkapi pemutar audio bawaan.

---

## Fitur Utama

### 1. Antarmuka Desktop Modern (GUI)
- **Desain Flat & Dark Theme**: Menggunakan palet warna elegan modern (Dracula / Catppuccin) yang bersih, profesional, dan nyaman di mata.
- **Pratinjau Cover & Metadata Real-time**: Menampilkan gambar cover resolusi tinggi serta informasi karya dari DLsite resmi:
  - Judul Lengkap Karya
  - Pengisi Suara (*Multi-CV / Seiyuu*)
  - Nama Lingkar Karya (*Circle / Maker*)
  - Rating Usia (*All-Ages / R18*)
  - Genre & Tag Karya
- **Tabel Antrean Fleksibel**: Mendukung input banyak kode RJ sekaligus (misal: `RJ01673437`, `RJ278932`, atau tautan URL) dipisahkan oleh spasi atau koma.
- **Penyimpanan Riwayat Koleksi**: Daftar riwayat karya yang pernah diunduh tersimpan secara otomatis, lengkap dengan statistik total koleksi, ukuran file di disk, dan cover thumbnail offline.

### 2. Pemutar Audio Bawaan (*Native Player*)
- **Pemutar Musik Terintegrasi**: Langsung mendengarkan karya yang baru saja diunduh atau dari daftar riwayat tanpa perlu membuka media player eksternal.
- **Kontrol Interaktif**:
  - *Timeline slider* interaktif (geser untuk lompat ke detik yang diinginkan).
  - Kontrol Volume (0% – 100%).
  - Tombol Navigasi: Putar / Jeda, Berhenti, Track Sebelumnya, dan Track Berikutnya.
  - Mode Pemutaran Berulang (*Loop Track: ON/OFF*).

### 3. Engine Unduhan Berkecepatan Tinggi
- **Akselerasi Multi-Thread**: Memanfaatkan engine `yt-dlp` yang dipercepat dengan `aria2c` (16 koneksi simultan per segmen).
- **Penggabungan Otomatis**: Otomatis menggabungkan multi-track HLS (`.m3u8`) maupun direct link (`.mp3`) menjadi satu file MP3 utuh.
- **Penyematan Metadata ID3v2.3**: Menggunakan `ffmpeg` untuk menanamkan cover art JPEG, judul, artis (CV), album (Circle), genre, dan komentar langsung ke dalam file audio.
- **Pembaruan Engine yt-dlp Mandiri**: Terdapat fitur pembaruan `yt-dlp` langsung di menu Pengaturan dengan pilihan channel **Stable** (rilis stabil resmi) atau **Nightly** (rilis harian fitur terbaru).

### 4. Manajemen Penyimpanan & Pengaturan
- **Ganti Folder Unduhan**: Bebas mengatur folder tujuan penyimpanan file audio.
- **Manajemen Cache**: Pantau dan bersihkan cache gambar cover art (`.cache/covers/`) serta file partisi sementara (`.cache/temp/`) dalam sekali klik.
- **Opsi Penamaan File**: Pilihan menggunakan kode RJ standar atau judul asli karya sebagai nama file MP3.

---

## Persyaratan Sistem

Sebelum menjalankan aplikasi dari *source code*, pastikan komponen berikut telah terpasang:

1. **Python 3.8+** (Disarankan Python 3.10 – 3.14)
2. **Pillow** (Untuk manipulasi gambar GUI):
   ```bash
   pip install Pillow
   ```
3. **Binary Pendukung** (letakkan di folder `bin/` atau daftarkan di system `PATH`):
   - **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**
   - **[aria2c](https://github.com/aria2/aria2)**
   - **[ffmpeg](https://ffmpeg.org/)**

---

## Cara Menjalankan

### 1. Menjalankan Mode Desktop GUI (Utama)
```bash
python main.py
```

### 2. Menjalankan Mode Terminal CLI
Jika Anda ingin menggunakan versi CLI interaktif berbasis command-line:
```bash
python cli.py
```

---

## Kompilasi Executable & Installer (Windows)

Project ini telah dilengkapi konfigurasi kompilasi binary C native via **Nuitka** dan pembuat installer via **Inno Setup**:

### 1. Kompilasi Standalone Binary (`JapaneseASMR.exe`)
Jalankan batch script build:
```cmd
.\nuitka_build.bat
```
Hasil executable mandiri tanpa console popup akan dibuat di dalam folder `dist/`.

### 2. Membuat Setup Installer (`JapaneseASMR_Setup_v1.0.0.exe`)
1. Buka file `installer_setup.iss` menggunakan **Inno Setup Compiler**.
2. Klik tombol **Compile** (atau tekan `Ctrl + F9`).
3. File setup installer siap pakai akan tersimpan di dalam folder `dist_installer/`.

---

## Struktur Direktori

```text
japaneseasmr-dl/
├── assets/                # Aset ikon dan grafis (app_icon.ico, app_icon.png)
├── bin/                   # Binary portabel (aria2c.exe, ffmpeg.exe, yt-dlp.exe)
├── config_manager.py      # Modul manajemen konfigurasi, riwayat, & scraper DLsite
├── gui.py                 # Modul antarmuka GUI Desktop, Player, & Settings
├── main.py                # Entry-point utama Desktop GUI
├── cli.py                 # Entry-point mandiri Terminal CLI
├── nuitka_build.bat       # Script kompilasi Nuitka ke Windows Executable
├── installer_setup.iss    # Script Inno Setup Compiler untuk installer Windows
├── README.md              # Dokumentasi project
└── downloads/             # Folder default penyimpanan hasil unduhan MP3
```

---

## Lisensi
Didistribusikan di bawah lisensi Open Source untuk penggunaan pribadi. Dibuat oleh **SayMaven**.
