# pdf_manual.py
# Modo 3: el profesor sube un PDF y especifica manualmente
# el título, autor, páginas y día de clase.

import json
from pdf_loader import (
    extract_pages_from_bytes,
    extract_all_pages_from_bytes,
    save_to_user_catalog,
    reload_catalog,
)

# Días de clase estándar — aplica a cualquier lectura
DAYS_DEFAULT = {
    "1": "Prepare to Read: Concept Vocabulary and Reading Strategy",
    "2": "Read the full text and complete Comprehension Check",
    "3": "Build Insight: First Thoughts, Summary and Analysis",
    "4": "Analyze and Interpret: Close Read and Literary Skill",
    "5": "Study Language and Craft: Vocabulary, Word Study and Grammar",
}


def process_manual_pdf(
    pdf_bytes:     bytes,
    pdf_name:      str,
    title:         str,
    author:        str,
    genre:         str,
    strategy:      str,
    vocabulary:    list,
    page_start:    int,
    page_end:      int,
    day:           str,
    grade_key:     str,
    unit_theme:    str,
    save_catalog:  bool = False,
) -> dict:
    """
    Procesa un PDF subido manualmente por el profesor.

    Parámetros:
    -----------
    pdf_bytes    : contenido del PDF en memoria (bytes)
    pdf_name     : nombre del archivo (ej: "mi_libro.pdf")
    title        : título de la lectura
    author       : autor
    genre        : género literario
    strategy     : estrategia de lectura
    vocabulary   : lista de palabras clave (puede estar vacía)
    page_start   : página de inicio del rango
    page_end     : página de fin del rango
    day          : día de clase ("1" a "5")
    grade_key    : clave del grado (ej: "10", "mi_libro")
    unit_theme   : tema de la unidad (ej: "Identity")
    save_catalog : si True, guarda el PDF completo en catalog_user.json

    Retorna dict compatible con el resto del pipeline.
    """

    # ── Extraer texto del rango indicado ─────────────────────────────────────
    text = extract_pages_from_bytes(pdf_bytes, page_start, page_end)

    if not text.strip():
        raise ValueError(
            f"No se pudo extraer texto de las páginas {page_start}–{page_end}. "
            f"Verifica que el PDF no esté protegido o escaneado como imagen."
        )

    # ── Agregar vocabulario al texto ─────────────────────────────────────────
    vocab_note = ""
    if vocabulary:
        vocab_note = (
            "\n\nKEY VOCABULARY FOR THIS READING:\n"
            + "\n".join(f"- {w}" for w in vocabulary)
        )

    # ── Guardar en catálogo si el profesor lo pide ────────────────────────────
    if save_catalog:
        texto_completo = extract_all_pages_from_bytes(pdf_bytes)
        reading_entry  = {
            "title":      title,
            "author":     author,
            "genre":      genre,
            "pages":      [page_start, page_end],
            "strategy":   strategy,
            "vocabulary": vocabulary,
            "days":       DAYS_DEFAULT,
        }
        save_to_user_catalog(
            grade_key      = grade_key,
            unit_theme     = unit_theme,
            pdf_name       = pdf_name,
            reading        = reading_entry,
            texto_completo = texto_completo,
        )

    day_description = DAYS_DEFAULT.get(day, "General lesson")

    return {
        "title":           title,
        "author":          author,
        "genre":           genre,
        "strategy":        strategy,
        "vocabulary":      vocabulary,
        "text":            text + vocab_note,
        "pages":           f"{page_start}–{page_end}",
        "day":             day,
        "day_description": day_description,
        "day_focus":       day_description,
        "source":          "manual",
    }


def get_manual_reading_text_by_day(
    grade_key:  str,
    reading_key: str,
    day:         str,
    pdf_bytes:   bytes,
) -> dict:
    """
    Para PDFs ya guardados en catalog_user.json:
    el profesor elige una nueva sección (páginas) del mismo PDF.
    No necesita volver a subir el archivo — usa el texto ya guardado.
    """
    from pdf_loader import CATALOG

    catalog    = reload_catalog()
    grade_data = catalog.get(grade_key)
    if not grade_data:
        raise ValueError(f"Grado '{grade_key}' no encontrado en el catálogo.")

    reading = grade_data["readings"].get(reading_key)
    if not reading:
        raise ValueError(f"Lectura '{reading_key}' no encontrada.")

    # Si el texto completo está guardado, extraer la sección proporcional
    if "texto_completo" in reading:
        start, end  = reading["pages"]
        total_pages = max(end - start, 1)
        lines       = reading["texto_completo"].split("\n")
        total_lines = len(lines)

        # Bloques por día
        PAGE_BLOCKS = {
            "1": (0.0,  0.2),
            "2": (0.2,  0.6),
            "3": (0.6,  0.75),
            "4": (0.75, 0.88),
            "5": (0.88, 1.0),
        }
        ratio_start, ratio_end = PAGE_BLOCKS.get(day, (0.0, 1.0))
        line_start = int(ratio_start * total_lines)
        line_end   = int(ratio_end   * total_lines)
        text       = "\n".join(lines[line_start:line_end])
    else:
        # Si no está guardado, extraer desde bytes
        start, end = reading["pages"]
        text = extract_pages_from_bytes(pdf_bytes, start, end)

    vocab_list = reading.get("vocabulary", [])
    vocab_note = ""
    if vocab_list:
        vocab_note = (
            "\n\nKEY VOCABULARY FOR THIS READING:\n"
            + "\n".join(f"- {w}" for w in vocab_list)
        )

    days            = reading.get("days", DAYS_DEFAULT)
    day_description = days.get(day, "General lesson")

    return {
        "title":           reading["title"],
        "author":          reading["author"],
        "genre":           reading["genre"],
        "strategy":        reading["strategy"],
        "vocabulary":      vocab_list,
        "text":            text + vocab_note,
        "pages":           f"{reading['pages'][0]}–{reading['pages'][1]}",
        "day":             day,
        "day_description": day_description,
        "day_focus":       day_description,
        "source":          "catalog_user",
    }