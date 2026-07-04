import json
from pathlib import Path

SETTINGS_PATH = Path(__file__).parent / "settings.json"

DEFAULTS = {
    "warn_days": 4,               # за сколько дней до срока предупреждать
    "notify_interval_hours": 6,   # как часто перепроверять сроки
    "currency": "\u20bd",         # символ валюты (по умолчанию ₽)
    "company_name": "WOOD METAL",
}


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            merged = DEFAULTS.copy()
            merged.update(data)
            return merged
        except Exception:
            return DEFAULTS.copy()
    return DEFAULTS.copy()


def save_settings(settings: dict):
    SETTINGS_PATH.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
    )
