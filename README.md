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

## Cara Instalasi & Penggunaan

### 1. Menggunakan Installer Windows (Direkomendasikan)
Bagi pengguna umum, Anda **tidak perlu menginstal Python atau alat tambahan apa pun**:
1. Unduh installer terbaru **`JapaneseASMR_Setup_v1.0.1.exe`** dari menu **[Releases](https://github.com/SayMaven/japaneseasmr-dl/releases)**.
2. Jalankan installer dan ikuti petunjuk pemasangan hingga selesai.
3. Aplikasi siap digunakan langsung dari Start Menu atau Desktop!

---

### 2. Menjalankan dari Source Code (Developer Mode)

Jika Anda ingin menjalankan atau mengembangkan langsung dari kode sumber (*source code*):

1. **Clone Repository**:
   ```bash
   git clone https://github.com/SayMaven/japaneseasmr-dl.git
   cd japaneseasmr-dl
   ```

2. **Instal Dependensi Python**:
   ```bash
   pip install Pillow
   ```

3. **Pastikan Binary Engine Tersedia**:
   Pastikan **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**, **[ffmpeg](https://ffmpeg.org/)**, dan **[aria2c](https://github.com/aria2/aria2)** telah terpasang di system PATH atau diletakkan di dalam folder `bin/`.

4. **Jalankan Aplikasi**:
   * **Mode Desktop GUI (Utama)**:
     ```bash
     python main.py
     ```
   * **Mode Terminal CLI (Interaktif)**:
     ```bash
     python cli.py
     ```

---

## Struktur Direktori Repository

```text
japaneseasmr-dl/
├── assets/                # Aset ikon dan grafis (icon.ico, icon.png)
├── config_manager.py      # Modul manajemen konfigurasi, riwayat, & scraper DLsite
├── gui.py                 # Modul antarmuka GUI Desktop, Player, & Settings
├── main.py                # Entry-point utama Desktop GUI
├── cli.py                 # Entry-point mandiri Terminal CLI
├── README.md              # Dokumentasi project
└── downloads/             # Folder penyimpanan hasil unduhan MP3
```

---

## Lisensi
Proyek ini dilisensikan di bawah **[GNU General Public License v3.0 (GPL-3.0)](LICENSE)**. Hak cipta © 2026 **SayMaven**.
