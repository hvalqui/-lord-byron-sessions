# pdf_router.py
# Enrutador central — decide qué modo usar según el origen del PDF
# y devuelve siempre el mismo formato de datos para el pipeline.
#
# Modo 1 — PDF conocido    : catálogo base (grade8, grade9)
# Modo 2 — PDF escaneado   : catalog_user.json con texto_completo
# Modo 3 — PDF manual      : el profesor ingresa los datos

from pdf_loader  import CATALOG, get_reading_text_by_day, reload_catalog
from pdf_manual  import process_manual_pdf, get_manual_reading_text_by_day
from pdf_scanner import get_scanned_reading_text_by_day


# ─────────────────────────────────────────────────────────────────────────────
# DETECCIÓN DE MODO
# ─────────────────────────────────────────────────────────────────────────────

def detect_mode(grade_key: str, reading_key: str) -> str:
    """
    Detecta automáticamente qué modo usar según el origen de la lectura.

    Retorna:
    --------
    "1" → PDF conocido (catalog_base.json)
    "2" → PDF escaneado (catalog_user.json con texto_completo)
    "3" → entrada manual sin texto guardado
    """
    catalog    = reload_catalog()
    grade_data = catalog.get(grade_key, {})
    reading    = grade_data.get("readings", {}).get(reading_key, {})

    if not reading:
        return "3"  # No existe en ningún catálogo → manual

    if "texto_completo" in reading:
        return "2"  # Texto guardado → escaneado o manual guardado

    # Está en catálogo pero sin texto guardado → PDF local (base)
    return "1"


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL DE ENRUTAMIENTO
# ─────────────────────────────────────────────────────────────────────────────

def get_reading_data(
    grade_key:   str,
    reading_key: str,
    day:         str,
    # Solo necesarios en Modo 3
    pdf_bytes:        bytes = None,
    pdf_name:         str   = "",
    title:            str   = "",
    author:           str   = "",
    genre:            str   = "",
    strategy:         str   = "",
    vocabulary:       list  = None,
    page_start:       int   = 1,
    page_end:         int   = 10,
    unit_theme:       str   = "",
    save_catalog:     bool  = False,
) -> dict:
    """
    Función única de acceso a lecturas — el resto del pipeline
    solo llama a esta función sin importar el modo.

    Detecta automáticamente el modo o usa Modo 3 si se pasan
    datos manuales.
    """
    vocabulary = vocabulary or []

    # Si se pasaron datos manuales → siempre Modo 3
    if title and pdf_bytes:
        return process_manual_pdf(
            pdf_bytes    = pdf_bytes,
            pdf_name     = pdf_name,
            title        = title,
            author       = author,
            genre        = genre,
            strategy     = strategy,
            vocabulary   = vocabulary,
            page_start   = page_start,
            page_end     = page_end,
            day          = day,
            grade_key    = grade_key,
            unit_theme   = unit_theme,
            save_catalog = save_catalog,
        )

    # Detectar modo automáticamente
    mode = detect_mode(grade_key, reading_key)

    if mode == "1":
        # PDF local en docs/ — catálogo base
        return get_reading_text_by_day(grade_key, reading_key, day)

    elif mode == "2":
        # Texto guardado en catalog_user.json
        return get_scanned_reading_text_by_day(grade_key, reading_key, day)

    else:
        # Modo 3 sin datos manuales — no debería llegar aquí
        # si el dashboard está bien implementado
        raise ValueError(
            f"Lectura '{reading_key}' del grado '{grade_key}' no encontrada "
            f"en ningún catálogo. Usa el Modo 3 para ingresarla manualmente."
        )


# ─────────────────────────────────────────────────────────────────────────────
# CATÁLOGO UNIFICADO PARA EL DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────

def get_full_catalog() -> dict:
    """
    Devuelve el catálogo completo (base + usuario) listo para
    poblar los menús del dashboard.
    Marca cada entrada con su modo de origen.
    """
    catalog = reload_catalog()
    result  = {}

    for grade_key, grade_data in catalog.items():
        result[grade_key] = {
            "unit_theme": grade_data.get("unit_theme", ""),
            "pdf":        grade_data.get("pdf", ""),
            "readings":   {}
        }
        for r_key, reading in grade_data["readings"].items():
            mode = "2" if "texto_completo" in reading else "1"
            result[grade_key]["readings"][r_key] = {
                "title":    reading.get("title",  ""),
                "author":   reading.get("author", ""),
                "genre":    reading.get("genre",  ""),
                "pages":    reading.get("pages",  []),
                "strategy": reading.get("strategy", ""),
                "vocabulary": reading.get("vocabulary", []),
                "days":     reading.get("days",   {}),
                "mode":     mode,   # "1" = local, "2" = guardado
            }

    return result


def get_grade_label(grade_key: str) -> str:
    """
    Devuelve la etiqueta del grado para mostrar en el dashboard.
    Ej: "8" → "Grade 8 — Rites of Passage"
        "u1" → "My Unit — Identity"
    """
    catalog    = reload_catalog()
    grade_data = catalog.get(grade_key, {})
    theme      = grade_data.get("unit_theme", "")

    # Claves numéricas → "Grade X"
    if grade_key.isdigit():
        return f"Grade {grade_key} — {theme}"

    # Claves de usuario → mostrar tal cual con el tema
    return f"{grade_key} — {theme}" if theme else grade_key


def get_mode_label(mode: str) -> str:
    """Etiqueta visual del modo para el dashboard."""
    return {
        "1": "📚 Catálogo base",
        "2": "💾 Guardado",
        "3": "✏️ Manual",
    }.get(mode, "")