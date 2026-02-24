# Database Management Commands

Berikut adalah panduan untuk menjalankan perintah database yang baru dibuat.

## Masalah Umum: "flask is not recognized"

Jika Anda mendapatkan error:
`flask: The term 'flask' is not recognized as a name of a cmdlet...`

Itu berarti **virtual environment belum aktif** atau path belum dikenali.

### Solusi 1: Panggil melalui `python -m flask` (Disarankan)

Cara paling aman adalah memanggil flask sebagai modul python:

```powershell
python -m flask reset-db
```

### Solusi 2: Aktifkan Virtual Environment

Pastikan venv aktif (jika folder venv Anda bernama `venv` atau `.venv`):

```powershell
# Windows
.\venv\Scripts\activate
# atau
.\.venv\Scripts\activate
```

Setelah aktif, barulah coba:

```powershell
flask reset-db
```

---

## Daftar Command

### 1. Reset Database (Hapus & Buat Ulang)

**PERHATIAN**: Ini akan menghapus SEMUA data di database.

```bash
# Cara standard
flask reset-db

# Cara alternatif (jika error path)
python -m flask reset-db
```

### 2. Migrasi Database (Mengubah Struktur Tabel)

Gunakan ini jika Anda mengubah model (misal menambah kolom di `models/biometric.py`).

1.  **Buat file migrasi**:
    ```bash
    python -m flask db migrate -m "penjelasan perubahan"
    ```
2.  **Terapkan ke database**:
    ```bash
    python -m flask db upgrade
    ```

### 3. Inisialisasi Migrasi (Hanya sekali di awal)

Jika folder `migrations/` belum ada:

```bash
python -m flask db init
```

---

## Bagi Pengguna Docker

Jika aplikasi berjalan di dalam Docker, perintah `flask` tidak akan dikenali di terminal host (Windows/Mac/Linux) kecuali Anda menginstall dependency di lokal juga.

**Solusi:** Jalankan perintah di dalam container.

### 1. Masuk ke Shell Container

```bash
docker exec -it biometric-service bash
# Setelah masuk, jalankan:
flask reset-db
```

### 2. Atau Jalankan Langsung dari Luar

```bash
docker exec -it biometric-service flask reset-db
```

Jika menggunakan Docker Compose:

```bash
docker-compose exec biometric-service flask reset-db
```
