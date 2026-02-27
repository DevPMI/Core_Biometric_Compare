# Biometric Service

Layanan API untuk registrasi, perbandingan, dan manajemen data biometrik (Wajah dan Telapak Tangan) menggunakan REST API.

## 🚀 Cara Deployment di Production

Langkah-langkah untuk menjalankan aplikasi ini di server production setelah melakukan _pull_ dari GitHub:

### Prasyarat

- **Docker** dan **Docker Compose** sudah terinstall di server.

### 1. Dapatkan Kode Terbaru (Clone atau Pull)

```bash
# Jika sudah di clone, gunakan git pull
cd Biometric_Service
git pull origin main
```

### 2. Konfigurasi Environment (`.env`)

Salin template konfigurasi `.env.example` ke `.env` lalu sesuaikan isinya:

```bash
cp .env.example .env
```

Ubah nilai-nilai yang penting di `.env`:

- `SECRET_KEY`: Ganti dengan kombinasi string acak yang aman.
- `API_KEY`: Ganti dengan password / kunci API rahasia yang kuat. Kunci ini harus dikirim di header pada setiap request client.
- `DATABASE_URL`: Biarkan default `postgresql://postgres:postgres@postgre-container:5432/User_Biometrics` jika menggunakan database bawaan dari docker-compose.

### 3. Setup Docker Network

Aplikasi ini terkonfigurasi untuk berjalan di network bernama `biometric-net`. Oleh karena itu, Anda harus membuatnya terlebih dahulu secara manual agar docker-compose bisa berjalan.

```bash
docker network create biometric-net
```

### 4. Konfigurasi Gunicorn Worker (Opsional)

Secara default, aplikasi ini diatur untuk menangani banyak request bersamaan menggunakan **4 worker Gunicorn** (ideal untuk CPU 2-Core). Jika server Anda memiliki CPU yang lebih besar, Anda bisa meningkatkan jumlah worker ini agar aplikasi bisa melayani lebih banyak antrean sekaligus.

Rumus rekomendasi untuk jumlah worker Gunicorn adalah: `(2 x Jumlah Core CPU) + 1`

Untuk mengubahnya, edit baris `CMD` di dalam file `Dockerfile`:

```dockerfile
# Ubah angka 4 menjadi jumlah worker yang Anda inginkan (misal: 9 untuk server 4-Core)
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:5000", "--timeout", "120", "run:app"]
```

### 5. Build dan Jalankan Aplikasi

Gunakan `docker-compose` untuk melakukan _build_ images dan menjalankannya di background (mode _detached_ `-d`):

```bash
docker-compose up -d --build
```

### 6. Inisialisasi Database (Wajib Pertama Kali Saja)

Setelah service dan database berjalan, Anda perlu membuat skema tabel database dengan menjalankan perintah berikut:

```bash
docker exec -it biometric-service flask reset-db
```

_(Peringatan: Jika Anda sedang me-restart, jangan jalankan `reset-db` lagi karena ini akan menghapus seluruh isi database!)_

Aplikasi Backend Service sekarang sudah aktif dan dapat diakses melalui port `5000` (`http://localhost:5000`).

---

## 📡 Dokumentasi Endpoint API

Semua endpoint bersifat dilindungi dan **memerlukan autentikasi** berupa header HTTP sebagai berikut:

```
X-API-Key: <isi-api-key-anda-di-file-env>
```

**Base URL API:** `http://<ip-server>:5000/api/v1/biometric`

### 1. Daftarkan Data Biometrik Baru (`/register`)

Digunakan untuk mendaftarkan wajah atau telapak tangan pengguna baru ke dalam database. Sistem akan otomatis menolak duplikasi biometrik.

- **URL:** `/register`
- **Method:** `POST`
- **Content-Type:** `multipart/form-data`
- **Body Input:**
  - `file`: Pilih file gambar (format: jpg, png, dll)
  - `type`: Isi dengan `face` atau `palm`
- **Response Sukses (201):** Mengembalikan data JSON beserta custom ID (contoh: `FACE-B9J3H129X`).

### 2. Cek Kecocokan Biometrik (`/compare`)

Dipakai pada proses login atau verifikasi. Alat ini akan menyocokkan file yang dikirim dengan seluruh database.

- **URL:** `/compare`
- **Method:** `POST`
- **Content-Type:** `multipart/form-data`
- **Body Input:**
  - `file`: Gambar langsung yang ingin diverifikasi
  - `type`: Isi dengan `face` atau `palm`
- **Response Sukses (200):** Menampilkan Data User (ID, level skor kemiripan) jika ada yang cocok dengan threshold yang dikonfigurasi.
- **Response Gagal (404):** Apabila tidak dicari temuan wajah / telapak yang cocok di database.

### 3. Ambil Daftar Semua Biometrik (`/`)

Mendapatkan laporan semua data biometrik yang sudah didaftarkan (dilengkapi paginasi).

- **URL:** `/`
- **Method:** `GET`
- **Query Parameter (Opsional):**
  - `type` (`face` / `palm`)
  - `page` (default: 1)
  - `limit` (default: 10)
- **Response Sukses (200):** Menampilkan daftar pengguna terdaftar beserta informasi paginasi.

### 4. Lihat Detail Biometrik Khusus (`/<id>`)

Menarik data spesifik mengenai satu ID biometrik saja.

- **URL:** `/<id>` (Contoh: `/FACE-A9B1C2D3`)
- **Method:** `GET`
- **Response Sukses (200):** Detail lengkap entri.

### 5. Hapus Data Biometrik (`/<id>`)

Menghapus seluruh rekaman data identitas beserta fotonya dari server. Berguna jika karyawan atau user sudah dinonaktifkan.

- **URL:** `/<id>` (Contoh: `/FACE-A9B1C2D3`)
- **Method:** `DELETE`
- **Response Sukses (200):** Konfirmasi bahwa datanya telah terhapus total dari sistem.
