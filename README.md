# 🎧 JapaneseASMR Downloader & Cover Art Embedder

Sebuah script downloader audio HLS/M3U8 otomatis dan penyemat cover art thumbnail untuk konten JapaneseASMR. Mendukung multi-connection parallel download via `aria2c` dan konversi ID3 metadata MP3 via `ffmpeg`.

---

## ✨ Fitur Utama

- 🚀 **Download Paralel Cepat**: Menggunakan `yt-dlp` dengan akselerasi multi-koneksi 16 paralel via `aria2c`.
- 🖼️ **Penyematan Cover Art**: Otomatis mengunduh cover dan menyematkannya ke dalam metadata MP3 (ID3v2 Album Art).
- 🔢 **Otomatisasi ID / Kode RJ**: Cukup masukkan kode produk (misal: `RJ01538146` atau `01538146`), URL m3u8, cover, dan nama output akan disusun otomatis.
- 📦 **Batch Multi-Download**: Mendukung input banyak ID sekaligus dipisahkan koma atau spasi.
- 📁 **Folder Output Teratur**: Hasil file MP3 otomatis disimpan ke folder `downloads/`.
- ⏭️ **Auto-Skip**: Otomatis mendeteksi dan melewati file yang sudah pernah diunduh sebelumnya.
- 🎨 **CLI Interaktif & Berwarna**: Tampilan terminal yang rapi dengan kode warna ANSI.
- 🔁 **Continuous Loop**: Kembali ke prompt input secara otomatis setelah unduhan selesai.

---

## 🛠️ Prasyarat (Dependencies)

Pastikan program-program berikut sudah terinstal di sistem Anda dan terdaftar di PATH:

1. **Python 3.8+** (untuk `main.py`)
2. **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**
3. **[aria2](https://github.com/aria2/aria2)** (`aria2c`)
4. **[ffmpeg](https://ffmpeg.org/)**
5. **curl** (bawaan Windows 10/11)

---

## 🚀 Cara Penggunaan

### 1. Versi Python (`main.py`) — *Direkomendasikan*

Jalankan script menggunakan Python:
```bash
python main.py
```

- Masukkan satu kode RJ atau beberapa kode sekaligus:
  ```text
  Masukkan Kode/Angka RJ: RJ01538146 RJ01595145 RJ01601293
  ```
- File `.mp3` hasil download akan tersimpan di dalam folder `downloads/`.

---

### 2. Versi Windows Batch (`main.bat`)

Klik ganda `main.bat` atau jalankan via terminal:
```cmd
.\main.bat
```
- Masukkan kode RJ yang diinginkan lalu tekan Enter.

---

## 📁 Struktur Project

```text
japaneseasmr-dl/
├── main.py        # Script utama versi Python (Fitur lengkap & Batch)
├── main.bat       # Script alternatif / cadangan versi Windows Batch
├── README.md      # Dokumentasi project
└── downloads/     # Folder penyimpanan file MP3 hasil download
```

---

## 📄 Lisensi
[MIT License](LICENSE)
