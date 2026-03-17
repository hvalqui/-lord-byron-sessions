# ejecutar_agente.py
import os
import pathlib
import webbrowser

from historial    import registrar, mostrar, ya_generada
from validar_html import validar
from grafo        import app
from pdf_loader   import show_menu        # show_menu ya fusiona base + usuario
from pdf_router   import get_reading_data  # enrutador central — Modo 1, 2 o 3
from exportar_docx import exportar_docx

print("==========================================")
print("   GENERADOR DE SESIONES LORD BYRON       ")
print("==========================================")
print("  [H] Ver historial de sesiones")
print("  [Enter] Generar nueva sesión")
print("------------------------------------------")
opcion_inicio = input("Tu elección: ").strip().lower()
if opcion_inicio == "h":
    mostrar()
    exit()

# ── 1. Selección de grado, lectura y día desde el catálogo ───────────────────
# show_menu() carga catalog_base.json + catalog_user.json automáticamente
# por lo que muestra tanto los PDFs conocidos como los agregados por el profesor
grade, reading_key, reading_data = show_menu()

# ── 2. Obtener texto usando el enrutador central ──────────────────────────────
# get_reading_data() detecta automáticamente el modo:
#   Modo 1 → PDF local en docs/  (catalog_base.json)
#   Modo 2 → texto guardado      (catalog_user.json con texto_completo)
#   Modo 3 → no aplica en terminal (requiere subir PDF desde dashboard)
try:
    reading_data = get_reading_data(
        grade_key   = grade,
        reading_key = reading_key,
        day         = reading_data["day"],
    )
except ValueError as e:
    print(f"\n⚠️  {e}")
    print("   Este PDF solo está disponible en el dashboard (Modo 3).")
    exit()

# ── 3. Advertencia si esta combinación ya fue generada ───────────────────────
if ya_generada(grade, reading_data["title"], reading_data["day"]):
    print(f"\n  ⚠️  ATENCIÓN: Ya generaste una sesión para:")
    print(f"     Grade {grade} — {reading_data['title']} — Día {reading_data['day']}")
    repetir = input("  ¿Generar de todas formas? (s/n): ").strip().lower()
    if repetir != "s":
        print("  Cancelado.")
        exit()

# ── 4. Datos de la sesión ─────────────────────────────────────────────────────
session_num   = input("\n✍️  Número de Sesión (ej: 03): ").strip() or "01"
chapter_topic = input("✍️  Chapter / Subtítulo del tema: ").strip()
if not chapter_topic:
    print("⚠️  Usando tema por defecto.")
    chapter_topic = "General Analysis"

# ── 5. Confirmación antes de generar ─────────────────────────────────────────
print(f"""
------------------------------------------
  SESIÓN {session_num} lista para generar:
  Grado     : {grade}
  Lectura   : {reading_data['title']}
  Autor     : {reading_data['author']}
  Género    : {reading_data['genre']}
  Estrategia: {reading_data['strategy']}
  Día       : {reading_data['day']} — {reading_data['day_description']}
  Chapter   : {chapter_topic}
  Páginas   : {reading_data['pages']}
  Fuente    : {reading_data.get('source', 'catalog_base')}
------------------------------------------""")

confirmar = input("¿Generar sesión? (Enter para sí / n para cancelar): ").strip().lower()
if confirmar == "n":
    print("Cancelado.")
    exit()

# ── 6. Preparar input para el agente ─────────────────────────────────────────
inputs = {
    "session_number":  session_num,
    "reading_title":   reading_data["title"].upper(),
    "topic":           chapter_topic,
    "grade":           grade,
    "source_text":     reading_data["text"],
    "day":             reading_data["day"],
    "day_description": reading_data["day_description"],
    "day_focus":       reading_data.get("day_focus", ""),
    "steps":           []
}

print(f"\n--- GENERANDO SESIÓN {session_num}: {reading_data['title']} ---")
estado_final = {}

# ── 7. Ejecutar el flujo ──────────────────────────────────────────────────────
for output in app.stream(inputs):
    for key, value in output.items():
        print(f"> Nodo '{key}' completado.")
        estado_final.update(value)

print("\n==========================================")
print("         PROCESO FINALIZADO               ")
print("==========================================")

# ── 8. Validar ────────────────────────────────────────────────────────────────
if "html_code" not in estado_final:
    print("\n[✘] Error: no se generó HTML. Revisa los nodos.")
    exit()

html_limpio = estado_final["html_code"].replace("```html", "").replace("```", "").strip()

es_valido, errores = validar(html_limpio)
if not es_valido:
    print("\n⚠️  ADVERTENCIA — El HTML tiene secciones faltantes:")
    for e in errores:
        print(e)
    continuar = input("\n¿Guardar de todas formas? (s/n): ").strip().lower()
    if continuar != "s":
        print("❌ Archivo no guardado. Revisa el contenido e intenta de nuevo.")
        exit()

# ── 9. Preparar rutas de salida ───────────────────────────────────────────────
reading_slug = (
    reading_data["title"]
    .replace(" ", "_")
    .replace("'", "")
    .replace(",", "")
)
output_dir = pathlib.Path(__file__).parent / "output" / f"grade{grade}"
output_dir.mkdir(parents=True, exist_ok=True)

filename_html = str(output_dir / f"Session_{session_num}_{reading_slug}.html")
filename_docx = str(output_dir / f"Session_{session_num}_{reading_slug}.docx")

# ── 10. Guardar HTML ──────────────────────────────────────────────────────────
with open(filename_html, "w", encoding="utf-8") as f:
    f.write(html_limpio)
print(f"\n[✔] HTML guardado: '{filename_html}'")

# ── 11. Exportar DOCX ────────────────────────────────────────────────────────
exportar_docx(
    approved_content = estado_final.get("approved_content")
                       or estado_final.get("lesson_content", "{}"),
    session_num      = session_num,
    reading_title    = reading_data["title"],
    chapter_topic    = chapter_topic,
    output_path      = filename_docx,
)
print(f"[✔] DOCX guardado:  '{filename_docx}'")

# ── 12. Registrar en historial ────────────────────────────────────────────────
registrar(
    session_num     = session_num,
    grade           = grade,
    reading_title   = reading_data["title"],
    day             = reading_data["day"],
    day_description = reading_data["day_description"],
    filename        = filename_html,
)
print(f"[✔] Sesión registrada en historial.")

# ── 13. Preview en navegador ──────────────────────────────────────────────────
webbrowser.open(f"file://{os.path.abspath(filename_html)}")
print(f"[✔] Abriendo preview en el navegador...")