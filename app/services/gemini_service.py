"""
Wrapper untuk semua pemanggilan ke Google Gemini.

Jika GEMINI_API_KEY tidak diset, semua fungsi akan mengembalikan
respons MOCK/dummy yang strukturnya tetap sama, supaya development
dan testing endpoint via Postman tidak terganggu.
"""
import json
import random
from typing import List, Dict, Any, Optional

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


def _parse_findings(text: str) -> List[str]:
    """Ubah output poin '- ...' dari Gemini menjadi list string bersih."""
    findings = []
    for line in text.strip().splitlines():
        line = line.strip()
        if line.startswith("- "):
            findings.append(line[2:].strip())
        elif line.startswith("-"):
            findings.append(line[1:].strip())
    return findings


def analyze_image(image_bytes: bytes, mime_type: str = "image/jpeg") -> Dict[str, Any]:
    prompt = (
        "Kamu adalah AI vision untuk membantu siswa SMA mengidentifikasi masalah nyata\n"
        "dari sebuah foto dalam pembelajaran Problem-Based Learning atau\n"
        "Project-Based Learning.\n"
        "Analisis gambar dan jelaskan hanya masalah yang benar-benar terlihat.\n"
        "Gambar dapat memuat berbagai jenis masalah, misalnya:\n"
        "- sampah organik, plastik, logam, kertas, atau limbah campuran;\n"
        "- jamur, lumut, noda biologis, atau kontaminasi;\n"
        "- genangan air, kebocoran, rembesan, atau kelembapan;\n"
        "- retakan, korosi, dan kerusakan bangunan;\n"
        "- kabel terbuka, stopkontak rusak, api, atau bahaya listrik;\n"
        "- tanaman layu, hama, atau penyakit tanaman;\n"
        "- saluran tersumbat, toilet kotor, debu, dan masalah kebersihan;\n"
        "- asap, pembakaran, pencemaran air, atau pencemaran udara;\n"
        "- objek dan kondisi bermasalah lainnya.\n"
        "ATURAN ANALISIS\n"
        "1. Jelaskan hanya masalah yang didukung oleh bukti visual pada gambar.\n"
        "2. Jangan mengarang objek atau kondisi yang tidak terlihat.\n"
        "3. Prioritaskan masalah utama, kemudian masalah pendukung jika ada.\n"
        "4. Jelaskan ciri visual yang membuat kondisi tersebut dianggap bermasalah.\n"
        "5. Jangan langsung memberikan solusi atau langkah penanganan.\n"
        "6. Jangan membuat diagnosis yang pasti hanya berdasarkan foto.\n"
        "7. Bedakan pengamatan visual dengan kemungkinan penyebab.\n"
        "8. Jika penyebab belum dapat dipastikan, gunakan kata:\n"
        '   "kemungkinan", "diduga", atau "dapat berkaitan dengan".\n'
        "9. Jika tidak terlihat masalah yang jelas, katakan bahwa masalah belum dapat\n"
        "   diidentifikasi dari gambar.\n"
        "10. Jangan menjelaskan benda normal yang tidak berkaitan dengan masalah.\n"
        "ATURAN KHUSUS JAMUR DAN PERTUMBUHAN BIOLOGIS\n"
        "Jika terlihat jamur, kapang, lumut, atau pertumbuhan biologis:\n"
        "- Jelaskan warna, pola, lokasi, dan luas pertumbuhan yang terlihat.\n"
        "- Gunakan identifikasi umum seperti:\n"
        '  "pertumbuhan jamur pada dinding",\n'
        '  "kapang berpigmen gelap",\n'
        '  atau "lapisan hijau menyerupai lumut".\n'
        "- Kamu boleh menyebut kandidat visual seperti:\n"
        '  "menyerupai Cladosporium",\n'
        '  "menyerupai Alternaria",\n'
        '  atau "menyerupai kelompok Aspergillus/Penicillium".\n'
        "- Jangan menyatakan jenis atau spesies jamur sebagai hasil yang pasti.\n"
        "- Jelaskan bahwa jenis pastinya tidak dapat dipastikan hanya melalui foto.\n"
        "- Warna hitam tidak otomatis berarti jamur beracun.\n"
        "FORMAT OUTPUT\n"
        "- Tulis dalam Bahasa Indonesia.\n"
        "- Gunakan 2-6 poin.\n"
        '- Setiap poin harus diawali dengan tanda "- ".\n'
        "- Setiap poin berisi satu temuan masalah yang jelas.\n"
        "- Urutkan dari masalah paling utama.\n"
        "- Jangan gunakan judul.\n"
        "- Jangan gunakan JSON.\n"
        "- Jangan gunakan markdown selain tanda poin.\n"
        "- Jangan gunakan code block.\n"
        "- Jangan menambahkan kalimat pembuka atau penutup."
    )

    if _gemini_ready:
        try:
            text = _call_gemini_vision(prompt, image_bytes, mime_type)
            findings = _parse_findings(text)
            if findings:
                return {"findings": findings}
        except Exception:
            pass  # fallback ke mock di bawah

    # ---- MOCK fallback ----
    return {
        "findings": [
            "Terlihat tumpukan sampah campuran (organik dan anorganik) di area yang difoto.",
            "Sebagian sampah tampak plastik dan kertas yang belum terpilah berdasarkan jenisnya.",
            "Kondisi ini kemungkinan berkaitan dengan belum adanya sistem pemilahan sampah di lokasi tersebut, tetapi penyebab pastinya belum dapat dipastikan hanya melalui foto.",
        ],
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

# ---------------------------------------------------------------------------
# 5. Module Topic Suggester (bukan generate URL, cuma rekomendasi topik)
# ---------------------------------------------------------------------------
def suggest_modules(problem_description: str) -> List[Dict[str, Any]]:
    prompt = (
        "Kamu adalah asisten guru SMA untuk pembelajaran PBL/PjBL. "
        f"Deskripsi masalah/studi kasus: {problem_description}\n\n"
        "Sarankan 4-6 topik materi pendukung yang relevan untuk membantu siswa memahami "
        "masalah ini. Kembalikan HANYA JSON (list), setiap item punya:\n"
        '{"title": "judul topik materi", "type": "dokumen" | "youtube" | "artikel", '
        '"reason": "alasan singkat kenapa topik ini relevan (1 kalimat)"}\n'
        "Field 'type' adalah SARAN jenis sumber yang paling cocok untuk topik itu, "
        "bukan link asli — guru akan mencari dan mengisi link sungguhan sendiri. "
        "Jangan mengarang URL apapun."
    )

    if _gemini_ready:
        try:
            text = _call_gemini_text(prompt)
            return _extract_json(text)
        except Exception:
            pass

    return [
        {"title": "Klasifikasi Sampah Organik dan Anorganik", "type": "artikel", "reason": "Dasar pemahaman kategori sampah sebelum memilah"},
        {"title": "Proses Daur Ulang Plastik", "type": "youtube", "reason": "Visualisasi proses daur ulang membantu siswa memahami tahapan teknis"},
        {"title": "Dampak Sampah terhadap Ekosistem", "type": "dokumen", "reason": "Memberi konteks urgensi masalah lingkungan"},
        {"title": "Prinsip 3R (Reduce, Reuse, Recycle)", "type": "artikel", "reason": "Kerangka solusi yang bisa diterapkan siswa"},
    ]


# ---------------------------------------------------------------------------
# 6. Trigger Questions (Pertanyaan Pemantik) dari Problem + Image Analysis
# ---------------------------------------------------------------------------
def generate_trigger_questions(
    problem_description: str, image_analysis: Optional[Dict[str, Any]] = None
) -> List[str]:
    analysis_text = ""
    if image_analysis and image_analysis.get("objects"):
        objects_summary = ", ".join(
            f"{obj['label']} ({obj['count']}x)" for obj in image_analysis["objects"]
        )
        analysis_text = f"Hasil deteksi objek pada foto: {objects_summary}. Total objek: {image_analysis.get('total_count', 0)}."

    prompt = (
        "Kamu adalah AI teman diskusi bergaya Socratic method untuk siswa SMA yang sedang "
        "menyelesaikan studi kasus PBL/PjBL.\n\n"
        f"Deskripsi masalah: {problem_description}\n"
        f"{analysis_text}\n\n"
        "Buatkan TEPAT 3 pertanyaan pemantik (trigger questions) untuk merangsang critical "
        "thinking siswa terhadap masalah ini. Pertanyaan harus:\n"
        "- Membuat siswa berpikir tentang AKAR PENYEBAB masalah (bukan solusi langsung)\n"
        "- Relevan dengan bidang keilmuan yang sesuai konteks (biologi, kimia, fisika, dll)\n"
        "- Singkat dan jelas, 1 kalimat per pertanyaan\n\n"
        "Kembalikan HANYA JSON array berisi 3 string, contoh:\n"
        '["Alasan biologis apa yang membuat tembok itu berjamur?", "...", "..."]'
    )

    if _gemini_ready:
        try:
            text = _call_gemini_text(prompt)
            result = _extract_json(text)
            if isinstance(result, list) and len(result) >= 3:
                return result[:3]
        except Exception:
            pass

    return [
        "Apa yang menyebabkan masalah ini bisa terjadi di lokasi tersebut?",
        "Faktor lingkungan apa yang paling berpengaruh terhadap kondisi ini?",
        "Bagaimana kondisi ini bisa berubah seiring waktu jika dibiarkan?",
    ]