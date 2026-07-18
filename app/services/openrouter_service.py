"""
Wrapper untuk generate gambar ilustrasi lewat OpenRouter.

Kuota API key OpenRouter TERBATAS (hanya 45 request total), jadi fungsi
ini WAJIB selalu dipanggil lewat check limit di router (lihat tasks.py),
jangan pernah dipanggil langsung tanpa validasi kuota.
"""
import base64
import requests

from app.config import settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

_openrouter_ready = bool(settings.OPENROUTER_API_KEY)


def generate_step_image(step_description: str) -> dict:
    """
    Generate 1 gambar ilustrasi untuk sebuah langkah kerja.
    Return: {"image_base64": str | None, "mode": "openrouter" | "mock"}
    """
    prompt = (
        f"Ilustrasi sederhana, gaya diagram edukasi untuk siswa SMA, "
        f"menggambarkan langkah kerja berikut: {step_description}. "
        f"Gaya flat, warna cerah, tanpa teks di dalam gambar."
    )

    if _openrouter_ready:
        try:
            response = requests.post(
                OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OPENROUTER_IMAGE_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "modalities": ["image", "text"],
                },
                timeout=60,
            )
            data = response.json()
            image_data = (
                data["choices"][0]["message"]
                .get("images", [{}])[0]
                .get("image_url", {})
                .get("url", "")
            )
            if image_data:
                return {"image_base64": image_data, "mode": "openrouter"}
        except Exception:
            pass  # fallback ke mock

    # ---- MOCK fallback: tidak ada gambar sungguhan, cuma penanda ----
    return {"image_base64": None, "mode": "mock"}