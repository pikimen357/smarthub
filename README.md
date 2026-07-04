# PBL SmartHub AI — Backend API

Backend **FastAPI** untuk **PBL SmartHub AI**, platform manajemen pembelajaran berbasis *Problem Based Learning* (PBL) & *Project Based Learning* (PjBL) yang dilengkapi AI Agent (Google Gemini) untuk diskusi Socratic, analisis gambar, generate rubrik, dan generate checklist kerja.

> ℹ️ Dokumen ini sengaja **tidak** membahas detail skema database atau daftar lengkap endpoint API, karena keduanya masih sangat mungkin berubah selama development. Untuk melihat endpoint yang tersedia saat ini, jalankan aplikasinya lalu buka **Swagger UI** di `http://localhost:8000/docs` — dokumentasi API di sana selalu sinkron dengan kode.

---

## 📖 Overview

Aplikasi ini menjembatani **Guru** dalam memberikan studi kasus nyata (misalnya masalah sampah kantin, pencemaran, reaksi kimia, dsb.) dan membantu **Siswa** memecahkan masalah tersebut secara sistematis melalui diskusi interaktif dengan AI menggunakan **Socratic method** — AI memberi pertanyaan pemancing, bukan jawaban langsung — hingga siswa merumuskan solusi dan menghasilkan checklist kerja serta laporan akhir.

Backend ini mengimplementasikan seluruh modul inti dari PRD:

- **Modul Guru:** manajemen kelas & token kelas, unggah foto masalah, CRUD modul materi, generate rubrik dengan AI, dashboard progres kelompok, review & grading laporan akhir.
- **Modul Siswa:** join kelas via token, lihat masalah + hasil deteksi objek dari AI, diskusi Socratic dengan AI, generate checklist (alat/bahan/langkah kerja) otomatis, isi laporan akhir + unggah foto bukti.
- **AI Agent (Gemini):**
  - *Image Analysis & Object Detection* — klasifikasi & hitung objek pada foto masalah, plus koordinat bounding box.
  - *AI Rubric Generator* — rubrik penilaian otomatis dari deskripsi masalah + modul materi.
  - *Stateful Socratic Chat* — chatbot yang mengingat konteks diskusi per kelompok.
  - *Auto-Generated Checklist* — merangkum hasil diskusi menjadi daftar alat, bahan, dan langkah kerja.

**Mode Mock AI:** Jika `GEMINI_API_KEY` belum diisi di `.env`, seluruh fitur AI di atas tetap berjalan menggunakan respons dummy/mock berstruktur sama, sehingga development dan testing endpoint (misalnya lewat Postman) tidak terganggu meski belum punya API key.

---

## 🔄 Alur Aplikasi (User Flow)

### Alur Guru
1. **Register/Login** sebagai guru.
2. **Buat Kelas Baru** → sistem menghasilkan Token Kelas unik (misal `KIMIA-882A`).
3. **Tambah Masalah** → unggah foto studi kasus & tulis deskripsi masalah. AI otomatis menganalisis foto (deteksi & hitung objek + bounding box).
4. **Tambah Modul** → unggah/tulis materi pendukung untuk kelas tersebut.
5. **Generate Rubrik dengan AI** → AI membuat rubrik penilaian berdasarkan deskripsi masalah + modul, guru bisa mengedit manual sebelum disimpan.
6. **Pantau Dashboard Kelas** → lihat progres setiap kelompok secara real-time (Belum Mulai → Diskusi AI → Praktik → Selesai).
7. **Review & Grading** → buka laporan akhir kelompok yang sudah "Selesai", beri nilai berdasarkan rubrik, tambahkan feedback.

### Alur Siswa
1. **Register/Login** sebagai siswa.
2. **Join Class** menggunakan Token Kelas dari guru.
3. **Lihat Masalah** → foto + deskripsi masalah, beserta hasil deteksi objek dari AI.
4. **AI Teman Diskusi** → chat dengan AI bergaya Socratic; AI memberi satu pertanyaan pemancing per waktu untuk merangsang critical thinking, tanpa memberi jawaban langsung.
5. **Generate Checklist** → setelah diskusi cukup, siswa klik generate — AI merangkum menjadi checklist Alat, Bahan, dan Langkah Kerja.
6. **Kerjakan Proyek Fisik** → centang checklist secara real-time sambil mengerjakan.
7. **Laporan Akhir** → tulis kesimpulan, unggah foto bukti pengerjaan, kirim ke guru.

Status kelompok berpindah otomatis mengikuti aktivitas: `belum_mulai → diskusi_ai → praktik → selesai`.

---

## 🛠 Tech Stack

- **Framework:** FastAPI (Python 3.11)
- **Database:** SQLite (via SQLAlchemy ORM) — cocok untuk MVP/prototype
- **Auth:** JWT (OAuth2 Password Flow) dengan role `teacher` / `student`
- **AI Service:** Google Gemini (`google-generativeai`), dengan fallback mock jika API key belum diset
- **Container:** Docker & Docker Compose

---

## 🚀 Menjalankan via Docker

### 1. Prasyarat
- [Docker](https://docs.docker.com/get-docker/) & [Docker Compose](https://docs.docker.com/compose/install/) sudah terpasang.

### 2. Masuk ke folder project

```bash
cd pbl-smarthub-backend
```

### 3. Siapkan file environment

```bash
cp .env.example .env
```

Buka `.env` dan sesuaikan bila perlu, terutama:

```env
SECRET_KEY=ganti-dengan-secret-key-anda
GEMINI_API_KEY=isi-jika-sudah-punya-api-key-gemini
```

> Jika `GEMINI_API_KEY` dikosongkan, aplikasi tetap bisa dijalankan dan ditest penuh — semua fitur AI akan memberi respons **mock** yang strukturnya identik dengan respons asli Gemini.

### 4. Build & jalankan container

```bash
docker compose up --build
```

Atau jalankan di background:

```bash
docker compose up --build -d
```

### 5. Cek aplikasi berjalan

- Health check: http://localhost:8001/
- Dokumentasi API interaktif (Swagger UI): http://localhost:8001/docs
- Dokumentasi API alternatif (ReDoc): http://localhost:8001/redoc

### 6. Menghentikan aplikasi

```bash
docker compose down
```

Data SQLite tersimpan di folder `./data` (di-mount sebagai volume), dan file upload tersimpan di `./app/static/uploads`, sehingga data tidak hilang saat container di-restart. Untuk reset total data, hapus isi kedua folder tersebut.

---

## 🧪 Testing API dengan Postman

1. Import file **`PBL_SmartHub_AI.postman_collection.json`** ke Postman (`Import` → pilih file).
2. Collection sudah dilengkapi **collection variables** (`base_url`, token, dsb.) dan **script otomatis** yang menyimpan `access_token`, `class_id`, `class_token`, `group_id`, dst. dari response ke variable, sehingga request-request berikutnya otomatis terisi tanpa copy-paste manual.
3. Jalankan request secara berurutan sesuai urutan folder:
   1. **1. Auth** — Register & Login (Guru dan Siswa)
   2. **2. Guru - Kelas & Modul** — buat kelas, isi masalah, unggah foto, tambah modul
   3. **3. Guru - Rubrik AI** — generate & kelola rubrik
   4. **4. Guru - Dashboard & Groups** — pantau progres kelompok
   5. **5. Siswa - Join & Problem Viewer** — siswa join kelas & lihat masalah
   6. **6. Siswa - Diskusi AI (Socratic)** — chat dengan AI
   7. **7. Siswa - Checklist & Laporan** — generate checklist, centang task, submit & grading laporan
   8. **8. Health Check**
4. Untuk request yang mengunggah file (`Upload Problem Image`, `Submit Final Report`), pilih file gambar secara manual pada tab **Body → form-data** sebelum mengirim request (Postman tidak bisa menyimpan path file lewat file collection).
5. Ganti `base_url` di collection variables jika API dijalankan di alamat/port lain.

---

## 📁 Struktur Folder

```
pbl-smarthub-backend/
├── app/
│   ├── main.py                # Entry point FastAPI
│   ├── config.py              # Konfigurasi (env variables)
│   ├── database.py            # Setup SQLAlchemy & session
│   ├── models.py              # Model database (SQLAlchemy)
│   ├── schemas.py              # Schema request/response (Pydantic)
│   ├── auth.py                 # Hashing password & JWT
│   ├── dependencies.py         # Dependency injection (auth, role guard)
│   ├── routers/                # Endpoint per modul (auth, classes, modules, dst.)
│   ├── services/
│   │   └── gemini_service.py   # Wrapper AI Gemini + mode mock
│   └── static/uploads/         # Folder penyimpanan file upload
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── PBL_SmartHub_AI.postman_collection.json
└── README.md
```

---

## 💡 Catatan Pengembangan Lanjutan

- Skema database & endpoint pada versi ini adalah implementasi awal untuk mendukung alur end-to-end sesuai PRD; sangat mungkin berubah/berkembang sesuai kebutuhan lomba/produk — silakan sesuaikan `models.py` dan router terkait.
- Untuk produksi, ganti `SECRET_KEY`, pertimbangkan migrasi ke PostgreSQL, dan tambahkan rate-limiting pada endpoint AI.
- Kelola migrasi skema database dengan Alembic bila skema mulai kompleks (belum termasuk pada versi ini agar tetap ringan untuk MVP).
