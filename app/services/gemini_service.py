"""
Wrapper untuk semua pemanggilan ke Google Gemini.

Jika GEMINI_API_KEY tidak diset, semua fungsi akan mengembalikan
respons MOCK/dummy yang strukturnya tetap sama, supaya development
dan testing endpoint via Postman tidak terganggu.
"""
import json
import random
from typing import List, Dict, Any

from app.config import settings

_gemini_ready = False

if settings.GEMINI_API_KEY:
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.GEMINI_API_KEY)
        _gemini_ready = True
    except Exception:
        _gemini_ready = False


def _call_gemini_text(prompt: str) -> str:
    """Panggil Gemini text model. Raise jika gagal, agar caller bisa fallback ke mock."""
    import google.generativeai as genai

    model = genai.GenerativeModel(settings.GEMINI_TEXT_MODEL)
    response = model.generate_content(prompt)
    return response.text


def _call_gemini_vision(prompt: str, image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    import google.generativeai as genai

    model = genai.GenerativeModel(settings.GEMINI_VISION_MODEL)
    response = model.generate_content(
        [prompt, {"mime_type": mime_type, "data": image_bytes}]
    )
    return response.text


def _extract_json(text: str) -> Any:
    """Bersihkan fenced code block ```json ... ``` sebelum parsing."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    return json.loads(cleaned.strip())


# ---------------------------------------------------------------------------
# 1. Image Analysis & Object Detection
# ---------------------------------------------------------------------------
def analyze_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> Dict[str, Any]:
    prompt = (
        "Kamu adalah AI vision untuk mendeteksi objek pada studi kasus siswa SMA "
        "(misal: sampah organik, anorganik, polimer, atau objek lain sesuai konteks foto). "
        "Analisis gambar ini dan kembalikan HANYA JSON valid dengan format:\n"
        '{"objects": [{"label": "sampah plastik", "count": 3, '
        '"bounding_boxes": [{"x": 10, "y": 20, "width": 50, "height": 60}]}], '
        '"total_count": 3}\n'
        "Koordinat bounding box dalam persen (0-100) relatif terhadap ukuran gambar. "
        "Jangan beri teks lain selain JSON."
    )

    if _gemini_ready:
        try:
            text = _call_gemini_vision(prompt, image_bytes, mime_type)
            return _extract_json(text)
        except Exception:
            pass  # fallback ke mock di bawah

    # ---- MOCK fallback ----
    return {
        "objects": [
            {
                "label": "sampah anorganik (plastik)",
                "count": 4,
                "bounding_boxes": [
                    {"x": 12, "y": 15, "width": 20, "height": 18},
                    {"x": 40, "y": 30, "width": 15, "height": 14},
                    {"x": 60, "y": 50, "width": 18, "height": 16},
                    {"x": 20, "y": 60, "width": 12, "height": 12},
                ],
            },
            {
                "label": "sampah organik",
                "count": 2,
                "bounding_boxes": [
                    {"x": 70, "y": 20, "width": 14, "height": 12},
                    {"x": 80, "y": 65, "width": 10, "height": 10},
                ],
            },
        ],
        "total_count": 6,
        "_mode": "mock",
    }


# ---------------------------------------------------------------------------
# 2. AI Rubric Generator
# ---------------------------------------------------------------------------
def generate_rubric(problem_description: str, modules_text: str) -> List[Dict[str, Any]]:
    prompt = (
        "Kamu adalah asisten guru SMA untuk pembelajaran PBL/PjBL. "
        f"Deskripsi masalah: {problem_description}\n"
        f"Materi pendukung: {modules_text}\n\n"
        "Buatkan rubrik penilaian dalam format HANYA JSON (list), setiap item punya "
        '"criteria", "description", dan "max_score" (integer, total idealnya menjadi 100 '
        "jika dijumlahkan proporsional). Buat 4-6 kriteria yang relevan "
        "(misalnya: pemahaman masalah, ketepatan langkah kerja, kerja sama kelompok, "
        "kualitas laporan akhir, kreativitas solusi)."
    )

    if _gemini_ready:
        try:
            text = _call_gemini_text(prompt)
            return _extract_json(text)
        except Exception:
            pass

    return [
        {"criteria": "Pemahaman Masalah", "description": "Ketepatan siswa merumuskan akar masalah", "max_score": 20},
        {"criteria": "Ketepatan Langkah Kerja", "description": "Kesesuaian langkah kerja dengan kaidah keilmuan", "max_score": 25},
        {"criteria": "Kerja Sama Kelompok", "description": "Kontribusi dan kolaborasi antar anggota", "max_score": 15},
        {"criteria": "Kualitas Laporan Akhir", "description": "Kejelasan kesimpulan dan bukti pengerjaan", "max_score": 25},
        {"criteria": "Kreativitas Solusi", "description": "Orisinalitas dan inovasi solusi yang diajukan", "max_score": 15},
    ]


# ---------------------------------------------------------------------------
# 3. Stateful Socratic Chat
# ---------------------------------------------------------------------------
def socratic_chat(
    problem_description: str,
    modules_text: str,
    chat_history: List[Dict[str, str]],
    student_message: str,
) -> str:
    history_text = "\n".join(
        f"{item['role']}: {item['message']}" for item in chat_history[-10:]
    )
    prompt = (
        "Kamu adalah AI teman diskusi bergaya Socratic method untuk siswa SMA yang sedang "
        "menyelesaikan studi kasus PBL/PjBL. Tugasmu HANYA memberikan SATU pertanyaan pemicu "
        "(trigger question) pada satu waktu untuk merangsang critical thinking. "
        "JANGAN memberikan jawaban akhir atau langkah kerja secara langsung.\n\n"
        f"Deskripsi masalah: {problem_description}\n"
        f"Materi pendukung: {modules_text}\n\n"
        f"Riwayat diskusi sebelumnya:\n{history_text}\n\n"
        f"Pesan terbaru dari siswa: {student_message}\n\n"
        "Balas dengan satu pertanyaan pemicu singkat (maks 2-3 kalimat), dalam Bahasa Indonesia."
    )

    if _gemini_ready:
        try:
            return _call_gemini_text(prompt).strip()
        except Exception:
            pass

    mock_questions = [
        "Menurutmu, apa yang menyebabkan masalah ini bisa terjadi di kantin sekolah?",
        "Kalau kamu perhatikan jenis sampahnya, mana yang paling banyak? Apa artinya bagi solusi kita?",
        "Materi yang sudah kamu baca menyebutkan proses apa yang relevan dengan kondisi ini?",
        "Apa dampak jangka panjang jika masalah ini tidak diselesaikan?",
        "Alat dan bahan apa saja yang mungkin dibutuhkan berdasarkan hipotesis awalmu?",
    ]
    return random.choice(mock_questions)


# ---------------------------------------------------------------------------
# 4. Auto-Generated Checklist (Alat, Bahan, Langkah Kerja)
# ---------------------------------------------------------------------------
def generate_checklist(
    problem_description: str, chat_history: List[Dict[str, str]]
) -> Dict[str, List[str]]:
    history_text = "\n".join(
        f"{item['role']}: {item['message']}" for item in chat_history
    )
    prompt = (
        "Berdasarkan diskusi Socratic berikut antara AI dan siswa mengenai studi kasus:\n"
        f"Masalah: {problem_description}\n\n"
        f"Riwayat diskusi:\n{history_text}\n\n"
        "Rangkum menjadi checklist kerja siswa. Kembalikan HANYA JSON dengan format:\n"
        '{"alat": ["..."], "bahan": ["..."], "langkah_kerja": ["langkah 1", "langkah 2"]}\n'
        "Langkah kerja harus berurutan sesuai kaidah keilmuan yang relevan."
    )

    if _gemini_ready:
        try:
            text = _call_gemini_text(prompt)
            return _extract_json(text)
        except Exception:
            pass

    return {
        "alat": ["Sarung tangan", "Wadah pemilah sampah", "Timbangan"],
        "bahan": ["Sampel sampah kantin", "Label kategori sampah"],
        "langkah_kerja": [
            "Kumpulkan sampel sampah dari kantin",
            "Pilah sampah berdasarkan kategori (organik/anorganik/polimer)",
            "Timbang dan catat jumlah tiap kategori",
            "Analisis proporsi tiap kategori terhadap total sampah",
            "Rumuskan solusi penanganan berdasarkan kategori dominan",
            "Dokumentasikan proses dan hasil untuk laporan akhir",
        ],
    }
