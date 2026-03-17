# pdf_loader.py
import os
import json
import fitz  # pymupdf

# ── Rutas ─────────────────────────────────────────────────────────────────────
DOCS_FOLDER    = os.path.join(os.path.dirname(__file__), "docs")
CATALOG_FOLDER = os.path.join(os.path.dirname(__file__), "catalog")
CATALOG_BASE   = os.path.join(CATALOG_FOLDER, "catalog_base.json")
CATALOG_USER   = os.path.join(CATALOG_FOLDER, "catalog_user.json")


# ── Carga del catálogo desde JSON ────────────────────────────────────────────

def _load_catalog() -> dict:
    """
    Carga y fusiona catalog_base.json + catalog_user.json.
    El catálogo del usuario tiene prioridad si hay claves repetidas.
    Las páginas se convierten de lista [x, y] a tupla (x, y) para
    mantener compatibilidad con el resto del código.
    """
    catalog = {}

    if os.path.exists(CATALOG_BASE):
        with open(CATALOG_BASE, encoding="utf-8") as f:
            catalog.update(json.load(f))

    if os.path.exists(CATALOG_USER):
        with open(CATALOG_USER, encoding="utf-8") as f:
            user_data = json.load(f)
            catalog.update(user_data)

    # Convertir páginas de lista a tupla en todas las lecturas
    for grade_data in catalog.values():
        for reading in grade_data.get("readings", {}).values():
            if isinstance(reading.get("pages"), list):
                reading["pages"] = tuple(reading["pages"])

    return catalog


def reload_catalog():
    """Recarga el catálogo desde disco — usar después de agregar un PDF nuevo."""
    global CATALOG
    CATALOG = _load_catalog()
    return CATALOG


# Catálogo disponible globalmente
CATALOG = _load_catalog()


# ── Guardar PDF nuevo en catálogo de usuario ──────────────────────────────────

def save_to_user_catalog(grade_key: str, unit_theme: str, pdf_name: str,
                          reading: dict, texto_completo: str):
    """
    Agrega una lectura nueva al catalog_user.json.
    Si el grade_key ya existe, agrega la lectura. Si no, crea la entrada.
    Las páginas se guardan como lista (JSON no soporta tuplas).
    """
    os.makedirs(CATALOG_FOLDER, exist_ok=True)

    user_catalog = {}
    if os.path.exists(CATALOG_USER):
        with open(CATALOG_USER, encoding="utf-8") as f:
            user_catalog = json.load(f)

    # Convertir tuplas a listas para JSON
    reading_serializable = {**reading}
    if isinstance(reading_serializable.get("pages"), tuple):
        reading_serializable["pages"] = list(reading_serializable["pages"])
    reading_serializable["texto_completo"] = texto_completo

    if grade_key not in user_catalog:
        user_catalog[grade_key] = {
            "pdf":        pdf_name,
            "unit_theme": unit_theme,
            "readings":   {"1": reading_serializable}
        }
    else:
        existing = user_catalog[grade_key]["readings"]
        next_key = str(len(existing) + 1)
        existing[next_key] = reading_serializable

    with open(CATALOG_USER, "w", encoding="utf-8") as f:
        json.dump(user_catalog, f, ensure_ascii=False, indent=2)

    reload_catalog()
    print(f"  ✔ '{reading['title']}' guardado en catalog_user.json")


# ── Extracción de texto desde archivo local ───────────────────────────────────

def extract_pages(pdf_filename: str, start_page: int, end_page: int) -> str:
    """
    Extrae texto de un rango de páginas del PDF local (en docs/).
    Las páginas se cuentan desde 1 (como en el libro físico).
    """
    pdf_path = os.path.join(DOCS_FOLDER, pdf_filename)

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(
            f"\n❌ No se encontró el archivo: {pdf_path}"
            f"\n   Asegúrate de colocar el PDF dentro de la carpeta 'docs/'"
        )

    doc   = fitz.open(pdf_path)
    total = doc.page_count
    text  = ""

    for page_num in range(start_page - 1, min(end_page, total)):
        text += doc[page_num].get_text()

    doc.close()
    return text.strip()


# ── Extracción de texto desde bytes (PDF subido desde el dashboard) ───────────

def extract_pages_from_bytes(pdf_bytes: bytes, start_page: int, end_page: int) -> str:
    """
    Extrae texto de un PDF cargado en memoria (bytes).
    Usado cuando el profesor sube un PDF desde el dashboard.
    """
    doc   = fitz.open(stream=pdf_bytes, filetype="pdf")
    total = doc.page_count
    text  = ""

    for page_num in range(start_page - 1, min(end_page, total)):
        text += doc[page_num].get_text()

    doc.close()
    return text.strip()


def extract_all_pages_from_bytes(pdf_bytes: bytes) -> str:
    """
    Extrae TODO el texto de un PDF en memoria.
    Usado al guardar un PDF nuevo en el catálogo de usuario por primera vez.
    """
    doc  = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text.strip()


# ── Extracción de texto completo desde catálogo de usuario ───────────────────

def _extract_from_saved_text(texto_completo: str, pg_start: int,
                              pg_end: int, start: int, end: int) -> str:
    """
    Cuando el texto ya está guardado en catalog_user.json,
    extrae la sección proporcional correspondiente al rango de páginas.
    """
    total_pages = max(end - start, 1)
    lines       = texto_completo.split("\n")
    total_lines = len(lines)
    ratio_start = (pg_start - start) / total_pages
    ratio_end   = (pg_end   - start) / total_pages
    line_start  = int(ratio_start * total_lines)
    line_end    = int(ratio_end   * total_lines)
    return "\n".join(lines[line_start:line_end])


# ── Extracción inteligente por día ────────────────────────────────────────────

def get_reading_text_by_day(grade: str, reading_key: str, day: str) -> dict:
    """
    Extrae secciones específicas del PDF según el día de clase.
    Funciona tanto con PDFs locales (docs/) como con texto guardado en el catálogo.
    """
    grade_data  = CATALOG[grade]
    reading     = grade_data["readings"][reading_key]
    start, end  = reading["pages"]
    total_pages = end - start
    p           = start

    PAGE_BLOCKS = {
        "1": {
            "pages": (p,                           p + 4),
            "focus": "concept vocabulary, reading strategy, text complexity, lesson overview",
        },
        "2": {
            "pages": (p + 4,                       p + int(total_pages * 0.6)),
            "focus": "full story text, background, comprehension check questions",
        },
        "3": {
            "pages": (p + int(total_pages * 0.6),  p + int(total_pages * 0.75)),
            "focus": "first thoughts, summary, analysis questions, essential question",
        },
        "4": {
            "pages": (p + int(total_pages * 0.75), p + int(total_pages * 0.88)),
            "focus": "close read practice, literary skill (plot development, diction, mood)",
        },
        "5": {
            "pages": (p + int(total_pages * 0.88), end),
            "focus": "concept vocabulary practice, word study, grammar, writing",
        },
    }

    block    = PAGE_BLOCKS.get(day, PAGE_BLOCKS["1"])
    pg_start = max(block["pages"][0], start)
    pg_end   = min(block["pages"][1], end)

    # ── Decidir fuente del texto ──────────────────────────────────────────────
    if "texto_completo" in reading:
        # PDF guardado en catalog_user.json — no necesita subir nada
        text = _extract_from_saved_text(
            reading["texto_completo"], pg_start, pg_end, start, end
        )
    else:
        # PDF local en docs/
        pdf_filename = grade_data.get("pdf", "")
        print(f"  📄 Extrayendo páginas {pg_start}–{pg_end} "
              f"(Día {day}: {block['focus']})")
        text = extract_pages(pdf_filename, pg_start, pg_end)

    # Vocabulario clave
    vocab_list = reading.get("vocabulary", [])
    vocab_note = ""
    if vocab_list:
        vocab_note = (
            "\n\nKEY VOCABULARY FOR THIS READING:\n"
            + "\n".join(f"- {w}" for w in vocab_list)
        )

    days = reading.get("days", {})

    return {
        "title":           reading["title"],
        "author":          reading["author"],
        "genre":           reading["genre"],
        "strategy":        reading["strategy"],
        "vocabulary":      vocab_list,
        "text":            text + vocab_note,
        "pages":           f"{pg_start}–{pg_end}",
        "day_focus":       block["focus"],
        "day":             day,
        "day_description": days.get(day, "General lesson"),
    }


# ── Lectura completa (sin filtro por día) — mantener por compatibilidad ───────

def get_reading_text(grade: str, reading_key: str) -> dict:
    """
    Devuelve el texto completo de una lectura sin filtrar por día.
    Se mantiene por compatibilidad con código existente.
    """
    grade_data = CATALOG.get(grade)
    if not grade_data:
        raise ValueError(f"Grado '{grade}' no encontrado en el catálogo.")

    reading = grade_data["readings"].get(reading_key)
    if not reading:
        raise ValueError(f"Lectura '{reading_key}' no encontrada para el grado {grade}.")

    start, end = reading["pages"]

    if "texto_completo" in reading:
        text = reading["texto_completo"]
    else:
        text = extract_pages(grade_data["pdf"], start, end)

    return {
        "title":      reading["title"],
        "author":     reading["author"],
        "genre":      reading["genre"],
        "strategy":   reading["strategy"],
        "vocabulary": reading["vocabulary"],
        "text":       text,
        "pages":      f"{start}–{end}"
    }


# ── Menú interactivo para terminal ───────────────────────────────────────────

def show_menu() -> tuple:
    """
    Muestra el menú interactivo en terminal.
    Devuelve (grade, reading_key, reading_data).
    """
    print("\n📚 SELECCIONA EL GRADO:")
    for g, data in CATALOG.items():
        print(f"   {g} → Grade {g}: {data['unit_theme']}")

    grade = input("\n🔢 Grado (8 o 9): ").strip()
    if grade not in CATALOG:
        print("⚠️  Grado no válido. Usando 9 por defecto.")
        grade = "9"

    grade_data = CATALOG[grade]
    print(f"\n📖 LECTURAS — Grade {grade}: {grade_data['unit_theme']}")
    for key, r in grade_data["readings"].items():
        print(f"   {key} → {r['title']} ({r['author']}) — {r['genre']}")

    reading_key = input("\n🔢 Número de lectura: ").strip()
    if reading_key not in grade_data["readings"]:
        print("⚠️  Lectura no válida. Usando la primera por defecto.")
        reading_key = "1"

    # Selección del día
    reading_info = grade_data["readings"][reading_key]
    days         = reading_info.get("days", {})

    if days:
        print(f"\n📅 DÍAS DE CLASE — {reading_info['title']}")
        for d, desc in days.items():
            print(f"   {d} → {desc}")
        day_key = input("\n🔢 Día de clase: ").strip()
        if day_key not in days:
            print("⚠️  Día no válido. Usando día 1.")
            day_key = "1"
        selected_day = days[day_key]
    else:
        day_key      = "1"
        selected_day = "General lesson"

    reading_data                    = get_reading_text_by_day(grade, reading_key, day_key)
    reading_data["day"]             = day_key
    reading_data["day_description"] = selected_day

    return grade, reading_key, reading_data
