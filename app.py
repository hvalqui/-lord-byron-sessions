# app.py
import os
import json
import pathlib
import streamlit as st
from dotenv import load_dotenv
from langchain_groq import ChatGroq

from pdf_router  import get_reading_data, get_full_catalog, get_grade_label, get_mode_label
from pdf_scanner import scan_pdf_structure, save_scanned_pdf, build_catalog_entry
from pdf_loader  import reload_catalog, extract_all_pages_from_bytes
from historial   import registrar, ya_generada
from validar_html import validar
from exportar_docx import exportar_docx
from guardrail   import es_input_valido, es_instruccion_pedagogica
from grafo       import app_web as agente

load_dotenv()

# ── MODO DESARROLLO (Groq - gratuito) ────────────────────────────────────────
llm = ChatGroq(model="llama-3.3-70b-versatile")

# ── MODO PRODUCCIÓN (descomentar cuando estés listo) ─────────────────────────
# from langchain_google_genai import ChatGoogleGenerativeAI
# llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")


# ── Configuración de página ───────────────────────────────────────────────────
st.set_page_config(
    page_title = "Lord Byron — Generador de Sesiones",
    page_icon  = "📚",
    layout     = "wide",
)

# ── Login ─────────────────────────────────────────────────────────────────────
def check_password():
    """Muestra pantalla de login y verifica el password."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    st.markdown("""
    <div style='text-align:center; padding:60px 0 20px 0;'>
        <span style='background:#166C52; color:white; padding:10px 28px;
                     border-radius:12px; font-size:1.8rem; font-weight:300;
                     font-family:Montserrat, Arial, sans-serif;'>
            GENERADOR DE SESIONES — LORD BYRON
        </span>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("### 🔐 Acceso")
        password = st.text_input(
            "Contraseña",
            type     = "password",
            placeholder = "Ingresa la contraseña..."
        )
        if st.button("Entrar", type="primary", use_container_width=True):
            if password == os.getenv("APP_PASSWORD", "lordbyron2025"):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("❌ Contraseña incorrecta.")

    return False

if not check_password():
    st.stop()


st.markdown("""
<style>
    body, .stApp { background-color: #ffffff !important; color: #1a1a1a !important; }
    .session-badge {
        background: #166C52; color: white;
        padding: 8px 24px; border-radius: 12px;
        font-size: 1.6rem; font-weight: 300;
        font-family: 'Montserrat', Arial, sans-serif;
        display: inline-block;
    }
    .block-label {
        background: #166C52; color: white;
        padding: 6px 18px; border-radius: 12px;
        font-size: 1.05rem; font-weight: 300;
        font-family: 'Montserrat', Arial, sans-serif;
        display: inline-block; margin: 12px 0 6px 0;
    }
    .activity-label {
        background: #3f7a63; color: white;
        padding: 5px 14px; border-radius: 16px;
        font-family: 'Comic Sans MS', cursive;
        font-size: 1rem; font-weight: 700;
        display: inline-block; margin: 6px 0;
    }
    .objective-header { color: rgb(255,51,102); font-weight: 700; font-size: 1rem; margin: 4px 0; }
    .objective-text   { font-family: Arial; font-size: 0.97rem; margin-bottom: 10px; }
    .instr-header     { color: #3366FF; font-weight: 700; font-size: 0.97rem; margin: 6px 0 2px 0; }
    .instr-item       { font-family: Arial; font-size: 0.95rem; margin-left: 16px; }
    .question-item    { font-family: Arial; font-size: 0.95rem; margin-left: 16px; color: #333; }
    .suggestion-box {
        background: #f0f7f4; border-left: 4px solid #166C52;
        padding: 12px 16px; border-radius: 6px;
        font-size: 0.93rem; white-space: pre-wrap; margin: 10px 0;
    }
    .divider-green { border: none; border-top: 2px solid #166C52; margin: 14px 0; }
    .guardrail-error {
        background: #fff0f0; border-left: 4px solid #ff3366;
        padding: 10px 14px; border-radius: 6px;
        font-size: 0.93rem; margin: 8px 0;
    }
    .mode-badge {
        font-size: 0.8rem; padding: 2px 8px;
        border-radius: 8px; margin-left: 6px;
    }
</style>
""", unsafe_allow_html=True)


# ── Título + botón salir ──────────────────────────────────────────────────────
col_titulo, col_salir = st.columns([6, 1])
with col_titulo:
    st.markdown("""
    <div style='text-align:center; padding:10px 0 20px 0;'>
        <span class='session-badge'>GENERADOR DE SESIONES — LORD BYRON</span>
    </div>
    """, unsafe_allow_html=True)
with col_salir:
    st.markdown("<div style='padding-top:18px;'>", unsafe_allow_html=True)
    if st.button("🚪 Salir", use_container_width=True, help="Cerrar la aplicación"):
        st.success("✔ Sesión finalizada. Cerrando servidor...")
        st.balloons()
        import time, os, signal, sys
        time.sleep(2)
        try:
            os.kill(os.getpid(), signal.SIGTERM)
        except Exception:
            sys.exit(0)
    st.markdown("</div>", unsafe_allow_html=True)

# ── Tabs principales ──────────────────────────────────────────────────────────
tab_generar, tab_pdfs, tab_historial = st.tabs([
    "📝 Generar Sesión",
    "📂 Mis PDFs",
    "📋 Historial",
])


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS LLM
# ─────────────────────────────────────────────────────────────────────────────

def _invoke_app(prompt: str) -> str:
    try:
        return llm.invoke(prompt).content
    except Exception as e:
        st.error(f"Error al llamar al modelo: {e}")
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS RENDER
# ─────────────────────────────────────────────────────────────────────────────

def render_objective(label: str, text: str):
    if not text.startswith("Students will"):
        text = "Students will " + text
    st.markdown(f"<div class='block-label'>{label}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='objective-header'>OBJECTIVE</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='objective-text'>{text}</div>", unsafe_allow_html=True)


def render_activity(act: dict):
    number = act.get("number", "01")
    emoji  = act.get("emoji", "")
    label  = act.get("label", f"ACTIVITY {number}")
    if label.startswith("ACTIVITY"):
        label = f"ACTIVITY {number}"
    st.markdown(f"<div class='activity-label'>{label} {emoji}</div>", unsafe_allow_html=True)
    for inst in act.get("instructions", []):
        parts = inst.split(" ", 1)
        if len(parts) == 2:
            st.markdown(
                f"<div class='instr-item'>• <strong>{parts[0]}</strong> {parts[1]}</div>",
                unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='instr-item'>• {inst}</div>", unsafe_allow_html=True)
    for q in act.get("questions", []):
        st.markdown(f"<div class='question-item'>❓ {q}</div>", unsafe_allow_html=True)


def render_session_content(data: dict, session_num: str,
                            reading_title: str, chapter_topic: str):
    st.markdown(f"""
    <div style='text-align:center; margin-bottom:6px;'>
        <span class='session-badge' style='font-size:1.2rem;'>SESSION {session_num}</span>
    </div>
    <h3 style='text-align:center; color:#166C52; font-family:Arial;
               font-size:1.5rem; margin:4px 0;'>{reading_title.upper()}</h3>
    <h4 style='text-align:center; color:#166C52; font-family:Arial;
               font-size:1.1rem; font-weight:500; margin:0 0 16px 0;'>{chapter_topic}</h4>
    <hr class='divider-green'>
    """, unsafe_allow_html=True)

    render_objective("LEADING FOR LEARNING", data.get("leading_objective", ""))
    if "leading_activity" in data:
        render_activity(data["leading_activity"])
    st.markdown("<hr class='divider-green'>", unsafe_allow_html=True)

    render_objective("BUILDING UP KNOWLEDGE", data.get("building_objective", ""))
    st.markdown("<hr class='divider-green'>", unsafe_allow_html=True)

    st.markdown("<div class='block-label'>BEFORE READING</div>", unsafe_allow_html=True)
    if "before_reading" in data:
        render_activity(data["before_reading"])
    st.markdown("<hr class='divider-green'>", unsafe_allow_html=True)

    st.markdown("<div class='block-label'>DURING READING</div>", unsafe_allow_html=True)
    if "during_reading" in data:
        render_activity(data["during_reading"])
    st.markdown("<hr class='divider-green'>", unsafe_allow_html=True)

    st.markdown("<div class='block-label'>AFTER READING</div>", unsafe_allow_html=True)
    if "after_reading" in data:
        render_activity(data["after_reading"])

    if "extra_activity" in data:
        st.markdown("<hr class='divider-green'>", unsafe_allow_html=True)
        render_activity(data["extra_activity"])


def generate_suggestions(data: dict, grade: str,
                          reading_title: str, topic: str) -> str:
    prompt = f"""
You are a senior curriculum reviewer for Lord Byron School (Grade {grade}).
Review this lesson plan and suggest SPECIFIC improvements.
Reading : {reading_title}
Topic   : {topic}

CURRENT LESSON:
{json.dumps(data, indent=2, ensure_ascii=False)}

Provide 3 to 5 concrete suggestions using this format:

SUGGESTION 1 — [section affected]
Current : "..."
Improved: "..."
Reason  : ...

Write in English. Be specific and pedagogically grounded.
"""
    return _invoke_app(prompt).strip()


def apply_changes(data: dict, instructions: str) -> dict:
    prompt = f"""
Apply these teacher instructions to the lesson plan JSON exactly as requested.
ONLY modify what is explicitly requested. Keep everything else unchanged.

CURRENT JSON:
{json.dumps(data, indent=2, ensure_ascii=False)}

TEACHER INSTRUCTIONS:
{instructions}

Return ONLY the updated raw JSON. No markdown. No commentary.
"""
    raw = _invoke_app(prompt).replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return data


def _procesar_cambios(cambios: str, data_json: dict, estado_final: dict,
                      con_sugerencias: bool = False,
                      suggestions: str = "") -> tuple:
    valido, motivo = es_input_valido(cambios)
    if not valido:
        return data_json, estado_final, False, f"🚫 {motivo}"
    if not es_instruccion_pedagogica(cambios, _invoke_app):
        return data_json, estado_final, False, (
            "⚠️ La instrucción no parece estar relacionada con la sesión de clase."
        )
    if con_sugerencias and suggestions:
        data_json = apply_changes(data_json, suggestions)
    data_json = apply_changes(data_json, cambios)
    estado_final["approved_content"] = json.dumps(data_json, ensure_ascii=False)
    return data_json, estado_final, True, "✔ Cambios aplicados correctamente."


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — GENERAR SESIÓN
# ═════════════════════════════════════════════════════════════════════════════
with tab_generar:

    col_izq, col_der = st.columns([1, 2])

    with col_izq:
        st.subheader("⚙️ Configuración")

        # Cargar catálogo completo (base + usuario)
        catalog = get_full_catalog()

        grade_key = st.selectbox(
            "Grado",
            options     = list(catalog.keys()),
            format_func = get_grade_label,
        )

        grade_data  = catalog[grade_key]
        readings    = grade_data["readings"]
        reading_key = st.selectbox(
            "Lectura",
            options     = list(readings.keys()),
            format_func = lambda k: (
                f"{readings[k]['title']} — {readings[k]['author']} "
                f"{get_mode_label(readings[k].get('mode','1'))}"
            )
        )
        reading_info = readings[reading_key]
        days         = reading_info.get("days", {})

        day_key = st.selectbox(
            "Día de clase",
            options     = list(days.keys()),
            format_func = lambda d: f"Día {d} — {days[d]}"
        )
        session_num   = st.text_input("Número de sesión", value="01", max_chars=3)
        chapter_topic = st.text_input(
            "Chapter / Subtítulo",
            placeholder = "ej: Coming of Age at the Sea"
        )

        st.divider()
        st.markdown(f"**Género:** {reading_info['genre']}")
        st.markdown(f"**Estrategia:** {reading_info.get('strategy','')}")
        if reading_info.get("vocabulary"):
            st.markdown(f"**Vocabulario:** {', '.join(reading_info['vocabulary'])}")
        st.markdown(f"**Fuente:** {get_mode_label(reading_info.get('mode','1'))}")

        if ya_generada(grade_key, reading_info["title"], day_key):
            st.warning(f"⚠️ Ya generaste **{reading_info['title']}** — Día {day_key}.")

        generar = st.button("🚀 Generar Sesión", type="primary", use_container_width=True)

    with col_der:

        if generar:
            if not chapter_topic.strip():
                st.error("⚠️ Ingresa el Chapter / Subtítulo antes de generar.")
                st.stop()

            valido, motivo = es_input_valido(chapter_topic)
            if not valido:
                st.markdown(
                    f"<div class='guardrail-error'>🚫 {motivo}</div>",
                    unsafe_allow_html=True)
                st.stop()

            with st.spinner("📄 Extrayendo texto del PDF..."):
                try:
                    reading_data = get_reading_data(grade_key, reading_key, day_key)
                except Exception as e:
                    st.error(str(e))
                    st.stop()

            with st.spinner("🤖 El agente está generando el contenido..."):
                inputs = {
                    "session_number":  session_num,
                    "reading_title":   reading_info["title"].upper(),
                    "topic":           chapter_topic,
                    "grade":           grade_key,
                    "source_text":     reading_data["text"],
                    "day":             day_key,
                    "day_description": days[day_key],
                    "day_focus":       reading_data.get("day_focus", ""),
                    "steps":           []
                }
                estado_final = {}
                for output in agente.stream(inputs):
                    for key, value in output.items():
                        estado_final.update(value)

            raw_content = (estado_final.get("approved_content")
                           or estado_final.get("lesson_content", "{}"))
            try:
                data_json = json.loads(raw_content)
            except Exception:
                data_json = {}

            with st.spinner("🔍 Generando sugerencias del agente..."):
                suggestions = generate_suggestions(
                    data_json, grade_key,
                    reading_info["title"], chapter_topic
                )

            st.session_state.update({
                "estado_final":  estado_final,
                "data_json":     data_json,
                "suggestions":   suggestions,
                "reading_info":  reading_info,
                "session_num":   session_num,
                "chapter_topic": chapter_topic,
                "grade_key":     grade_key,
                "day_key":       day_key,
                "days":          days,
            })

        if "data_json" not in st.session_state:
            st.info("Configura los parámetros y pulsa **🚀 Generar Sesión**.")
            st.stop()

        data_json     = st.session_state["data_json"]
        suggestions   = st.session_state["suggestions"]
        estado_final  = st.session_state["estado_final"]
        reading_info  = st.session_state["reading_info"]
        session_num   = st.session_state["session_num"]
        chapter_topic = st.session_state["chapter_topic"]
        grade_key     = st.session_state["grade_key"]
        day_key       = st.session_state["day_key"]
        days          = st.session_state["days"]

        t_contenido, t_revision, t_preview, t_html = st.tabs([
            "📋 Contenido generado",
            "✏️ Revisión y cambios",
            "🌐 Preview HTML",
            "📄 Código HTML",
        ])

        with t_contenido:
            st.markdown("### Contenido generado por el agente")
            render_session_content(
                data_json, session_num,
                reading_info["title"], chapter_topic
            )

        with t_revision:
            st.markdown("### 🤖 Sugerencias del agente")
            st.markdown(
                f"<div class='suggestion-box'>{suggestions}</div>",
                unsafe_allow_html=True
            )
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                aplicar_sugerencias = st.button(
                    "✅ Aplicar sugerencias del agente",
                    use_container_width=True
                )
            with col_s2:
                st.button("⏭️ Ignorar sugerencias", use_container_width=True)

            if aplicar_sugerencias:
                with st.spinner("Aplicando sugerencias..."):
                    data_json = apply_changes(data_json, suggestions)
                    st.session_state["data_json"] = data_json
                    estado_final["approved_content"] = json.dumps(data_json, ensure_ascii=False)
                    st.session_state["estado_final"] = estado_final
                st.success("✔ Sugerencias aplicadas.")
                st.rerun()

            st.divider()
            st.markdown("### ✏️ Tus propios cambios")
            st.caption(
                "Escribe en lenguaje natural — solo instrucciones relacionadas a la sesión. "
                "Ej: *'Agrega una instrucción en DURING READING sobre el vocabulario craving'*"
            )

            col_texto, col_envio = st.columns([11, 1])
            with col_texto:
                cambios_profesor = st.text_area(
                    "Describe los cambios que quieres hacer",
                    placeholder = "Escribe aquí tus instrucciones pedagógicas...",
                    height      = 120,
                    key         = "cambios_profesor"
                )
            with col_envio:
                st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
                enviar = st.button(
                    "➤",
                    use_container_width=True,
                    help="Enviar mis cambios al agente",
                    key="btn_enviar"
                )
                st.markdown("""
                <style>
                div[data-testid="stButton"] button[key="btn_enviar"] {
                    background-color: #166C52 !important;
                    color: white !important;
                    font-size: 1.3rem !important;
                    border-radius: 50% !important;
                    height: 60px !important;
                    border: none !important;
                }
                </style>
                """, unsafe_allow_html=True)

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                aplicar_profesor = st.button(
                    "✅ Aplicar mis cambios",
                    use_container_width=True,
                    key="btn_aplicar_profesor"
                )
            with col_p2:
                aplicar_ambos = st.button(
                    "✅ Sugerencias + mis cambios",
                    use_container_width=True,
                    key="btn_aplicar_ambos"
                )

            if enviar:
                aplicar_profesor = True

            if aplicar_profesor and cambios_profesor.strip():
                with st.spinner("Aplicando tus cambios..."):
                    data_json, estado_final, ok, mensaje = _procesar_cambios(
                        cambios=cambios_profesor, data_json=data_json,
                        estado_final=estado_final, con_sugerencias=False,
                    )
                if ok:
                    st.session_state["data_json"]    = data_json
                    st.session_state["estado_final"] = estado_final
                    st.success(mensaje)
                    st.rerun()
                else:
                    st.markdown(
                        f"<div class='guardrail-error'>{mensaje}</div>",
                        unsafe_allow_html=True)

            if aplicar_ambos and cambios_profesor.strip():
                with st.spinner("Aplicando sugerencias + tus cambios..."):
                    data_json, estado_final, ok, mensaje = _procesar_cambios(
                        cambios=cambios_profesor, data_json=data_json,
                        estado_final=estado_final, con_sugerencias=True,
                        suggestions=suggestions,
                    )
                if ok:
                    st.session_state["data_json"]    = data_json
                    st.session_state["estado_final"] = estado_final
                    st.success(mensaje)
                    st.rerun()
                else:
                    st.markdown(
                        f"<div class='guardrail-error'>{mensaje}</div>",
                        unsafe_allow_html=True)

            st.divider()
            st.markdown("### 👁️ Contenido actualizado")
            render_session_content(
                data_json, session_num,
                reading_info["title"], chapter_topic
            )

        with t_preview:
            html_code   = estado_final.get("html_code", "")
            html_limpio = html_code.replace("```html", "").replace("```", "").strip()
            if html_limpio:
                st.components.v1.html(html_limpio, height=850, scrolling=True)
            else:
                st.info("El preview aparecerá aquí después de guardar.")

        with t_html:
            html_code   = estado_final.get("html_code", "")
            html_limpio = html_code.replace("```html", "").replace("```", "").strip()
            st.code(html_limpio, language="html")

        st.divider()
        reading_slug  = (
            reading_info["title"]
            .replace(" ", "_").replace("'", "").replace(",", "")
        )
        output_dir    = pathlib.Path(__file__).parent / "output" / f"grade{grade_key}"
        output_dir.mkdir(parents=True, exist_ok=True)
        filename_html = str(output_dir / f"Session_{session_num}_{reading_slug}.html")
        filename_docx = str(output_dir / f"Session_{session_num}_{reading_slug}.docx")

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            es_valido, errores = validar(html_limpio)
            if not es_valido:
                st.warning("⚠️ HTML incompleto:\n" + "\n".join(errores))
            if st.button("💾 Guardar HTML", use_container_width=True):
                with open(filename_html, "w", encoding="utf-8") as f:
                    f.write(html_limpio)
                registrar(
                    session_num     = session_num,
                    grade           = grade_key,
                    reading_title   = reading_info["title"],
                    day             = day_key,
                    day_description = days[day_key],
                    filename        = filename_html,
                )
                st.success("✔ HTML guardado.")

        with col_b:
            if st.button("📝 Exportar DOCX", use_container_width=True):
                exportar_docx(
                    approved_content = (
                        estado_final.get("approved_content")
                        or estado_final.get("lesson_content", "{}")
                    ),
                    session_num   = session_num,
                    reading_title = reading_info["title"],
                    chapter_topic = chapter_topic,
                    output_path   = filename_docx,
                )
                st.success("✔ DOCX guardado.")

        with col_c:
            st.download_button(
                label               = "⬇️ Descargar HTML",
                data                = html_limpio.encode("utf-8"),
                file_name           = f"Session_{session_num}_{reading_slug}.html",
                mime                = "text/html",
                use_container_width = True,
            )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — MIS PDFs (subir y gestionar PDFs nuevos)
# ═════════════════════════════════════════════════════════════════════════════
with tab_pdfs:
    st.subheader("📂 Gestión de PDFs")

    modo_pdf = st.radio(
        "¿Cómo quieres agregar un PDF nuevo?",
        ["🤖 Escanear automáticamente (el agente detecta las lecturas)",
         "✏️ Ingresar datos manualmente"],
        horizontal=True,
    )

    st.divider()

    # ── Uploader común a ambos modos ─────────────────────────────────────────
    pdf_file = st.file_uploader(
        "📄 Sube tu PDF aquí",
        type=["pdf"],
        help="El archivo se procesa en memoria y no se almacena en el servidor."
    )

    if pdf_file:
        pdf_bytes = pdf_file.read()
        pdf_name  = pdf_file.name
        st.success(f"✔ PDF cargado: **{pdf_name}** ({len(pdf_bytes)//1024} KB)")

        # ────────────────────────────────────────────────────────────────────
        # MODO 2 — Escaneo automático
        # ────────────────────────────────────────────────────────────────────
        if "automático" in modo_pdf:
            st.markdown("### 🤖 Escaneo automático")
            st.caption("El agente analizará las primeras páginas del PDF para detectar su estructura.")

            if st.button("🔍 Escanear PDF", type="primary"):
                with st.spinner("Analizando estructura del PDF..."):
                    scan_result = scan_pdf_structure(pdf_bytes, _invoke_app)
                st.session_state["scan_result"] = scan_result
                st.session_state["scan_pdf_bytes"] = pdf_bytes
                st.session_state["scan_pdf_name"]  = pdf_name

            if "scan_result" in st.session_state:
                scan_result = st.session_state["scan_result"]
                st.markdown("### 📋 Resultado del escaneo")
                st.caption("Revisa y corrige si es necesario antes de guardar.")

                # Mostrar y permitir editar lo detectado
                unit_theme_detected = scan_result.get("unit_theme", "")
                grade_hint          = scan_result.get("grade_hint", "")

                col_t, col_g = st.columns(2)
                with col_t:
                    unit_theme_final = st.text_input(
                        "Tema de la unidad",
                        value = unit_theme_detected
                    )
                with col_g:
                    grade_key_new = st.text_input(
                        "Clave del grado (ej: 10, 11, mi_libro)",
                        value = grade_hint or "10"
                    )

                readings_detected = scan_result.get("readings", [])
                if readings_detected:
                    st.markdown(f"**Lecturas detectadas ({len(readings_detected)}):**")
                    for i, r in enumerate(readings_detected):
                        with st.expander(f"{i+1}. {r.get('title', 'Sin título')}"):
                            st.write(f"**Autor:** {r.get('author', '')}")
                            st.write(f"**Género:** {r.get('genre', '')}")
                            st.write(f"**Páginas:** {r.get('page_start', 0)} – {r.get('page_end', 0)}")
                            st.write(f"**Estrategia:** {r.get('strategy', '')}")
                            if r.get("vocabulary"):
                                st.write(f"**Vocabulario:** {', '.join(r['vocabulary'])}")
                else:
                    st.warning("No se detectaron lecturas. Intenta con el modo manual.")

                st.divider()
                if st.button("💾 Guardar en catálogo", type="primary"):
                    with st.spinner("Guardando PDF completo en el catálogo..."):
                        save_scanned_pdf(
                            pdf_bytes           = st.session_state["scan_pdf_bytes"],
                            pdf_name            = st.session_state["scan_pdf_name"],
                            grade_key           = grade_key_new,
                            scan_result         = scan_result,
                            unit_theme_override = unit_theme_final,
                        )
                    st.success(
                        f"✔ PDF guardado con {len(readings_detected)} lecturas. "
                        f"Ya aparece en el menú de **Generar Sesión**."
                    )
                    # Limpiar estado
                    for k in ["scan_result", "scan_pdf_bytes", "scan_pdf_name"]:
                        st.session_state.pop(k, None)
                    st.rerun()

        # ────────────────────────────────────────────────────────────────────
        # MODO 3 — Ingreso manual
        # ────────────────────────────────────────────────────────────────────
        else:
            st.markdown("### ✏️ Ingreso manual de datos")

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                m_title    = st.text_input("Título de la lectura *", placeholder="ej: The Gift of the Magi")
                m_author   = st.text_input("Autor *",                placeholder="ej: O. Henry")
                m_genre    = st.text_input("Género",                 placeholder="ej: Short Story")
                m_strategy = st.text_input("Estrategia de lectura",  placeholder="ej: Make Inferences")
            with col_m2:
                m_grade_key  = st.text_input("Clave del grado *",  placeholder="ej: 10, 11, mi_libro")
                m_unit_theme = st.text_input("Tema de la unidad",  placeholder="ej: Identity and Change")
                m_page_start = st.number_input("Página de inicio *", min_value=1,  value=1)
                m_page_end   = st.number_input("Página de fin *",    min_value=1,  value=20)

            m_vocab_raw = st.text_input(
                "Vocabulario clave (separado por comas)",
                placeholder="ej: sacrifice, irony, coincidence"
            )
            m_vocab = [v.strip() for v in m_vocab_raw.split(",") if v.strip()]

            m_day = st.selectbox(
                "Día de clase para esta sesión",
                options=["1","2","3","4","5"],
                format_func=lambda d: {
                    "1": "Día 1 — Vocabulario y estrategia",
                    "2": "Día 2 — Lectura completa",
                    "3": "Día 3 — Análisis y reflexión",
                    "4": "Día 4 — Close Read",
                    "5": "Día 5 — Lenguaje y gramática",
                }[d]
            )

            m_save = st.checkbox(
                "💾 Guardar en catálogo para uso futuro",
                value=True,
                help="Si marcas esto, la próxima vez no necesitarás subir el PDF."
            )

            st.divider()
            if st.button("🚀 Procesar PDF manual", type="primary"):
                if not m_title or not m_author or not m_grade_key:
                    st.error("⚠️ Título, autor y clave del grado son obligatorios.")
                else:
                    with st.spinner("Extrayendo texto del rango indicado..."):
                        try:
                            from pdf_manual import process_manual_pdf
                            reading_data = process_manual_pdf(
                                pdf_bytes    = pdf_bytes,
                                pdf_name     = pdf_name,
                                title        = m_title,
                                author       = m_author,
                                genre        = m_genre,
                                strategy     = m_strategy,
                                vocabulary   = m_vocab,
                                page_start   = int(m_page_start),
                                page_end     = int(m_page_end),
                                day          = m_day,
                                grade_key    = m_grade_key,
                                unit_theme   = m_unit_theme,
                                save_catalog = m_save,
                            )
                            st.session_state["manual_reading_data"] = reading_data
                            st.session_state["manual_grade_key"]    = m_grade_key
                            if m_save:
                                st.success(
                                    f"✔ '{m_title}' guardado en el catálogo. "
                                    f"Ya aparece en **Generar Sesión**."
                                )
                            else:
                                st.success(
                                    f"✔ Texto extraído de páginas {m_page_start}–{m_page_end}. "
                                    f"Ve a **Generar Sesión** para continuar."
                                )
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))

    # ── Catálogo del usuario ──────────────────────────────────────────────────
    st.divider()
    st.markdown("### 📚 PDFs en tu catálogo")

    catalog = get_full_catalog()
    user_entries = {
        k: v for k, v in catalog.items()
        if any(
            r.get("mode") == "2"
            for r in v["readings"].values()
        )
    }

    if not user_entries:
        st.info("Aún no has agregado PDFs al catálogo. Sube uno arriba.")
    else:
        for gk, gv in user_entries.items():
            st.markdown(f"**{get_grade_label(gk)}**")
            for rk, rv in gv["readings"].items():
                if rv.get("mode") == "2":
                    st.markdown(
                        f"- 💾 {rv['title']} — {rv['author']} "
                        f"*(págs. {rv['pages'][0]}–{rv['pages'][1]})*"
                    )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — HISTORIAL
# ═════════════════════════════════════════════════════════════════════════════
with tab_historial:
    st.subheader("📋 Sesiones generadas")

    HISTORIAL_FILE = pathlib.Path(__file__).parent / "historial.json"

    if not HISTORIAL_FILE.exists():
        st.info("No hay sesiones registradas aún.")
    else:
        with open(HISTORIAL_FILE, encoding="utf-8") as f:
            historial = json.load(f)

        if not historial:
            st.info("No hay sesiones registradas aún.")
        else:
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filtro_grado = st.selectbox(
                    "Filtrar por grado",
                    ["Todos"] + sorted(set(e["grade"] for e in historial))
                )
            with col_f2:
                filtro_lectura = st.selectbox(
                    "Filtrar por lectura",
                    ["Todas"] + sorted(set(e["reading"] for e in historial))
                )

            filtrado = [
                e for e in historial
                if (filtro_grado   == "Todos" or e["grade"]   == filtro_grado)
                and (filtro_lectura == "Todas" or e["reading"] == filtro_lectura)
            ]

            import pandas as pd
            df = pd.DataFrame(filtrado)
            if not df.empty:
                df.columns = ["Fecha", "Sesión", "Grado", "Lectura",
                              "Día", "Descripción", "Archivo"]
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.caption(f"{len(filtrado)} sesión(es) encontrada(s).")