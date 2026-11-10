# 🤖 LinkedIn & RevoU Career Companion Automation Agent

Agen otomatisasi berbasis Python & Selenium untuk mencari lowongan, melakukan job matching, apply lowongan di LinkedIn, mengirim connection request + note ke recruiter, mengambil bukti screenshot, dan mencatatnya ke **RevoU Career Companion Application Tracker**.

---

## 🎯 Target & Spesifikasi
* **Kandidat:** Nasaruddin, ST (Junior Software Engineer / Backend Developer)
* **RevoU CV Profile:** `Nasaruddin,ST2`
* **Target Role:** Junior Backend Developer, Junior Software Engineer, Full Stack Developer (Node.js, TypeScript, NestJS, PostgreSQL)
* **Target Wilayah Lowongan:** Remote Luar Negeri (Australia, United States, Eropa, Jepang, Uni Emirat Arab / Arab Saudi / Qatar)
* **Volume:** Minimal 10 apply per minggu (dapat diatur via CLI)
* **Tipe LinkedIn:** Akun Free (catatan koneksi recruiter dibatasi ringkas ≤ 200 karakter dengan fallback aman)

---

## 🔄 Alur Kerja Pipeline (4 Fase)

```
[1. Job Matching RevoU]
       │
       ▼  (Pilih CV: Nasaruddin,ST2 di https://next.revou.tech/dashboard/quality-application/job-matching)
[2. LinkedIn Easy Apply]
       │
       ▼  (Isi form otomatis + upload ATS CV - Nasaruddin.pdf + Screenshot Bukti Submit)
[3. Recruiter Outreach]
       │
       ▼  (Connect + Note personalisasi ke Recruiter / Job Poster + Screenshot Bukti Permintaan)
[4. RevoU Tracker Submit]
       │
       ▼  (Isi form https://next.revou.tech/dashboard/quality-application/application + Upload Bukti)
[5. Selesai & Log Tersimpan di data/applied_tracker.json]
```

---

## 📁 Struktur File Proyek

* [`config.py`](file:///mnt/sda3/naz/Software%20Engineer/otomatis_apply/config.py): Konfigurasi target role, negara, URL RevoU & LinkedIn, limit aplikasi, path direktori.
* [`profile_data.py`](file:///mnt/sda3/naz/Software%20Engineer/otomatis_apply/profile_data.py): Data kandidat dari ATS CV, database jawaban screening question (pengalaman, tools, availability), generator pesan recruiter.
* [`browser_manager.py`](file:///mnt/sda3/naz/Software%20Engineer/otomatis_apply/browser_manager.py): Engine browser Selenium dengan fitur anti-deteksi bot, persistent user profile, dan screenshot handler.
* [`linkedin_engine.py`](file:///mnt/sda3/naz/Software%20Engineer/otomatis_apply/linkedin_engine.py): Pencarian lowongan LinkedIn Remote + Easy Apply, autofill modal apply, dan koneksi ke recruiter beserta screenshot.
* [`revou_companion.py`](file:///mnt/sda3/naz/Software%20Engineer/otomatis_apply/revou_companion.py): Otomasi RevoU Career Companion (Job Matching & Submit Quality Application Tracker + upload bukti).
* [`orchestrator.py`](file:///mnt/sda3/naz/Software%20Engineer/otomatis_apply/orchestrator.py): Master orchestrator yang menjalankan pipeline end-to-end dengan safe delays antar-apply.
* [`run_agent.sh`](file:///mnt/sda3/naz/Software%20Engineer/otomatis_apply/run_agent.sh): Shell script cepat untuk menjalankan agen.
* `screenshots/`: Direktori penyimpanan otomatis semua bukti screenshot lamaran dan outreach.
* `data/applied_tracker.json`: Database riwayat seluruh lowongan yang sudah berhasil diapply.

---

## 🚀 Cara Menjalankan Agen

### Metode 1: Menjalankan Langsung dengan Profile Tersimpan (Rekomendasi)
Jalankan perintah berikut di terminal:
```bash
./run_agent.sh --run --count 10
```
* Chrome akan terbuka secara otomatis.
* Jika belum login di RevoU atau LinkedIn, script akan memberikan jeda di terminal: silakan login sekali saja di jendela browser yang terbuka, lalu tekan `ENTER` di terminal.
* Sesi login akan tersimpan permanen di folder `browser_profile/` sehingga untuk eksekusi berikutnya tidak perlu login ulang.

### Metode 2: Hubungkan ke Chrome Harian yang Sedang Terbuka
Jika Anda sudah login di LinkedIn dan RevoU di Google Chrome Anda sendiri:
1. Tutup Chrome yang sedang aktif, lalu buka kembali dari terminal dengan flag debugging:
   ```bash
   google-chrome --remote-debugging-port=9222 &
   ```
2. Jalankan agen dengan flag `--connect-existing`:
   ```bash
   ./run_agent.sh --run --connect-existing --count 10
   ```
   Agen akan langsung memakai tab dan sesi aktif tanpa perlu login ulang.

---

## 📊 Melihat Rekap Lamaran
Untuk memeriksa progres lamaran yang sudah dikerjakan dan link buktinya:
```bash
./run_agent.sh --status
```
