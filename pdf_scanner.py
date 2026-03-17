# pdf_scanner.py
# Modo 2: el agente escanea un PDF nuevo, detecta su estructura
# y genera el catálogo automáticamente.

import json
import fitz  # pymupdf
from pdf_loader import (
    extract_all_pages_from_bytes,
    save_to_user_catalog,
    reload_catalog,
)

# Número de páginas a escanear para detectar la estructura del PDF
SCAN_PAGES = 15


def _extract_scan_sample(pdf_bytes: bytes) -> str:
    """
    Extrae las primeras SCAN_PAGES páginas del PDF para que
    el LLM pueda detectar su estructura sin procesar todo el documento.
    """
    doc   = fitz.open(stream=pdf_bytes, filetype="pdf")
    total = doc.page_count
    text  = ""
    for i in range(min(SCAN_PAGES, total)):
        text += f"\n--- PÁGINA {i+1} ---\n"
        text += doc[i].get_text()
    doc.close()
    return text.strip()


def scan_pdf_structure(pdf_bytes: bytes, invoke_fn) -> dict:
    """
    Usa el LLM para analizar las primeras páginas del PDF
    y detectar automáticamente su estructura.

    Parámetros:
    -----------
    pdf_bytes : contenido del PDF en memoria
    invoke_fn : función _invoke_with_retry o _invoke_app

    Retorna dict con la estructura detectada.
    """
    sample_text = _extract_scan_sample(pdf_bytes)

    prompt = f"""
You are analyzing a Teacher's Edition textbook PDF to extract its structure.

Read the following text from the first {SCAN_PAGES} pages and identify:
1. The unit theme or title
2. All reading selections (stories, articles, poems) with their details

Return ONLY a valid JSON object with this exact structure:

{{
  "unit_theme": "Name of the unit (e.g., Survival, Rites of Passage)",
  "grade_hint": "Grade level if mentioned (e.g., 9, 8) or empty string",
  "readings": [
    {{
      "title":      "Title of the reading",
      "author":     "Author name",
      "genre":      "Genre (Short Story, Poem, Article, etc.)",
      "page_start": 0,
      "page_end":   0,
      "strategy":   "Reading strategy if mentioned (e.g., Make Connections)",
      "vocabulary": ["word1", "word2"]
    }}
  ]
}}

RULES:
- If page numbers are not clearly stated, estimate based on the table of contents
- If vocabulary is not listed, use an empty array
- If a field is unknown, use an empty string
- Return ONLY raw JSON. No markdown. No commentary.

PDF CONTENT:
{sample_text[:4000]}
"""

    raw = invoke_fn(prompt).replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Si el LLM no devuelve JSON válido, retornar estructura mínima
        return {
            "unit_theme": "Unknown Unit",
            "grade_hint": "",
            "readings":   []
        }


def build_catalog_entry(scan_result: dict, pdf_name: str,
                         grade_key: str, unit_theme_override: str = "") -> dict:
    """
    Convierte el resultado del escaneo en una entrada válida para el catálogo.

    Parámetros:
    -----------
    scan_result        : resultado de scan_pdf_structure()
    pdf_name           : nombre del archivo PDF
    grade_key          : clave del grado elegida por el profesor (ej: "10")
    unit_theme_override: si el profesor corrigió el tema, usar este valor

    Retorna dict listo para guardar en catalog_user.json.
    """
    unit_theme = unit_theme_override or scan_result.get("unit_theme", "Unknown Unit")

    # Días estándar que aplican a cualquier lectura
    days_default = {
        "1": "Prepare to Read: Concept Vocabulary and Reading Strategy",
        "2": "Read the full text and complete Comprehension Check",
        "3": "Build Insight: First Thoughts, Summary and Analysis",
        "4": "Analyze and Interpret: Close Read and Literary Skill",
        "5": "Study Language and Craft: Vocabulary, Word Study and Grammar",
    }

    readings = {}
    for i, r in enumerate(scan_result.get("readings", []), 1):
        readings[str(i)] = {
            "title":      r.get("title",    "Unknown Title"),
            "author":     r.get("author",   "Unknown Author"),
            "genre":      r.get("genre",    "Unknown Genre"),
            "pages":      [r.get("page_start", 1), r.get("page_end", 10)],
            "strategy":   r.get("strategy", ""),
            "vocabulary": r.get("vocabulary", []),
            "days":       days_default,
        }

    return {
        grade_key: {
            "pdf":        pdf_name,
            "unit_theme": unit_theme,
            "readings":   readings,
        }
    }


def save_scanned_pdf(pdf_bytes: bytes, pdf_name: str,
                     grade_key: str, scan_result: dict,
                     unit_theme_override: str = ""):
    """
    Guarda el PDF escaneado completo en catalog_user.json.
    Extrae TODO el texto y lo asocia a cada lectura.
    """
    texto_completo = extract_all_pages_from_bytes(pdf_bytes)
    unit_theme     = unit_theme_override or scan_result.get("unit_theme", "Unknown Unit")

    days_default = {
        "1": "Prepare to Read: Concept Vocabulary and Reading Strategy",
        "2": "Read the full text and complete Comprehension Check",
        "3": "Build Insight: First Thoughts, Summary and Analysis",
        "4": "Analyze and Interpret: Close Read and Literary Skill",
        "5": "Study Language and Craft: Vocabulary, Word Study and Grammar",
    }

    for r in scan_result.get("readings", []):
        reading_entry = {
            "title":      r.get("title",      "Unknown Title"),
            "author":     r.get("author",     "Unknown Author"),
            "genre":      r.get("genre",      "Unknown Genre"),
            "pages":      [r.get("page_start", 1), r.get("page_end", 10)],
            "strategy":   r.get("strategy",   ""),
            "vocabulary": r.get("vocabulary", []),
            "days":       days_default,
        }
        save_to_user_catalog(
            grade_key      = grade_key,
            unit_theme     = unit_theme,
            pdf_name       = pdf_name,
            reading        = reading_entry,
            texto_completo = texto_completo,
        )

    reload_catalog()
    print(f"  ✔ PDF '{pdf_name}' guardado con "
          f"{len(scan_result.get('readings', []))} lecturas.")


def get_scanned_reading_text_by_day(grade_key: str, reading_key: str,
                                     day: str) -> dict:
    """
    Obtiene el texto de una lectura ya escaneada y guardada en catalog_user.json,
    extrayendo la sección proporcional al día de clase.
    No requiere subir el PDF nuevamente.
    """
    from pdf_loader import CATALOG

    catalog    = reload_catalog()
    grade_data = catalog.get(grade_key)
    if not grade_data:
        raise ValueError(f"Grado '{grade_key}' no encontrado.")

    reading = grade_data["readings"].get(reading_key)
    if not reading:
        raise ValueError(f"Lectura '{reading_key}' no encontrada.")

    start, end  = reading["pages"]
    total_pages = max(end - start, 1)

    # Proporciones por día
    DAY_RATIOS = {
        "1": (0.0,  0.2),
        "2": (0.2,  0.6),
        "3": (0.6,  0.75),
        "4": (0.75, 0.88),
        "5": (0.88, 1.0),
    }

    texto_completo = reading.get("texto_completo", "")
    ratio_start, ratio_end = DAY_RATIOS.get(day, (0.0, 1.0))

    if texto_completo:
        lines      = texto_completo.split("\n")
        total_lines = len(lines)
        line_start  = int(ratio_start * total_lines)
        line_end    = int(ratio_end   * total_lines)
        text        = "\n".join(lines[line_start:line_end])
    else:
        text = ""

    vocab_list = reading.get("vocabulary", [])
    vocab_note = ""
    if vocab_list:
        vocab_note = (
            "\n\nKEY VOCABULARY FOR THIS READING:\n"
            + "\n".join(f"- {w}" for w in vocab_list)
        )

    days            = reading.get("days", {})
    day_description = days.get(day, "General lesson")

    return {
        "title":           reading["title"],
        "author":          reading["author"],
        "genre":           reading["genre"],
        "strategy":        reading["strategy"],
        "vocabulary":      vocab_list,
        "text":            text + vocab_note,
        "pages":           f"{start}–{end}",
        "day":             day,
        "day_description": day_description,
        "day_focus":       day_description,
        "source":          "scanned",
    }