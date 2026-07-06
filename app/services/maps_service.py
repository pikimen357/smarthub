"""
Wrapper untuk Google Maps API (Geocoding + Static Maps).

Jika GOOGLE_MAPS_API_KEY tidak diset, fungsi geocode/reverse_geocode
mengembalikan data MOCK yang strukturnya tetap sama, dan static_map_url
mengembalikan None, supaya development/testing tidak terganggu.
"""
from typing import Optional, Dict, Any

import requests

from app.config import settings

GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
STATIC_MAP_URL = "https://maps.googleapis.com/maps/api/staticmap"

_maps_ready = bool(settings.GOOGLE_MAPS_API_KEY)


def geocode_address(address: str) -> Dict[str, Any]:
    """Ubah alamat teks -> {latitude, longitude, formatted_address}."""
    if _maps_ready:
        try:
            resp = requests.get(
                GEOCODE_URL,
                params={"address": address, "key": settings.GOOGLE_MAPS_API_KEY},
                timeout=10,
            )
            data = resp.json()
            if data.get("status") == "OK" and data.get("results"):
                result = data["results"][0]
                location = result["geometry"]["location"]
                return {
                    "latitude": location["lat"],
                    "longitude": location["lng"],
                    "formatted_address": result.get("formatted_address", address),
                }
        except Exception:
            pass  # fallback ke mock di bawah

    # ---- MOCK fallback: koordinat dummy area Semarang, Jawa Tengah ----
    return {
        "latitude": -6.9932,
        "longitude": 110.4203,
        "formatted_address": f"{address} (mock location - Semarang, Jawa Tengah)",
    }


def reverse_geocode(latitude: float, longitude: float) -> str:
    """Ubah koordinat -> alamat teks."""
    if _maps_ready:
        try:
            resp = requests.get(
                GEOCODE_URL,
                params={
                    "latlng": f"{latitude},{longitude}",
                    "key": settings.GOOGLE_MAPS_API_KEY,
                },
                timeout=10,
            )
            data = resp.json()
            if data.get("status") == "OK" and data.get("results"):
                return data["results"][0].get("formatted_address", "")
        except Exception:
            pass

    return f"Lokasi ({latitude:.4f}, {longitude:.4f}) - mock address"


def static_map_url(latitude: float, longitude: float, zoom: int = 16, size: str = "600x400") -> Optional[str]:
    """Bangun URL Static Map dengan pin di koordinat tersebut. None jika API key belum diset."""
    if not _maps_ready:
        return None

    marker = f"color:red|{latitude},{longitude}"
    return (
        f"{STATIC_MAP_URL}?center={latitude},{longitude}&zoom={zoom}"
        f"&size={size}&markers={marker}&key={settings.GOOGLE_MAPS_API_KEY}"
    )