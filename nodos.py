import os
import json
import time
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from estado import AgentState

# Cargamos variables de entorno
load_dotenv()

# ── MODO DESARROLLO (Groq - gratuito) ────────────────────────────────────────
llm = ChatGroq(model="llama-3.3-70b-versatile")

# ── MODO PRODUCCIÓN (descomentar cuando estés listo) ─────────────────────────
# from langchain_google_genai import ChatGoogleGenerativeAI
# llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")


# ─────────────────────────────────────────────────────────────────────────────
# HELPER: llamada al LLM con reintento automático ante rate limit
# ─────────────────────────────────────────────────────────────────────────────

def _invoke_with_retry(prompt: str, max_retries: int = 3) -> str:
    """Llama al LLM con reintento automático si hay rate limit."""
    for attempt in range(max_retries):
        try:
            response = llm.invoke(prompt)
            return response.content
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e) or "rate_limit" in str(e).lower():
                wait = (attempt + 1) * 5
                print(f"  ⚠️  Rate limit. Esperando {wait}s antes de reintentar...")
                time.sleep(wait)
            else:
                raise
    raise Exception("❌ Límite de API alcanzado después de varios intentos.")


# ─────────────────────────────────────────────────────────────────────────────
# NODO 1: Profesor de Literatura → genera contenido en JSON estructurado
# ─────────────────────────────────────────────────────────────────────────────

def literature_professor_node(state: AgentState):
    """
    Genera el contenido académico basado en el texto REAL del PDF.
    """
    print(f"\n[Agente Literatura] Analizando texto fuente...")

    source_text     = state.get("source_text", "").strip()
    grade           = state.get("grade", "9")
    topic           = state.get("topic", "")
    title           = state.get("reading_title", "")
    day             = state.get("day", "1")
    day_description = state.get("day_description", "General lesson")
    day_focus       = state.get("day_focus", "")

    if source_text:
        context_block = f"""
BASE YOUR ENTIRE LESSON STRICTLY on this text extracted from the Teacher's Edition
(myPerspectives Grade {grade}), specifically selected for Day {day} of the lesson.

This day's focus: {day_description}
Content type   : {day_focus}

Do NOT invent content. Use ONLY what appears in the source text below.
If the source includes vocabulary words, use them. If it includes
specific questions or tasks from the book, adapt them for the activities.

--- SOURCE TEXT START ---
{source_text}
--- SOURCE TEXT END ---
"""
    else:
        context_block = (
            "No source text provided. "
            "Generate based on general knowledge of the topic."
        )

    prompt = f"""
You are an expert Professor of English Literature designing a Moodle lesson
for Grade {grade} students at Lord Byron School.

Reading title   : {title}
Chapter/Topic   : {topic}
Day of class    : Day {day} of 5 — {day_description}

{context_block}

TASK: Generate ONLY a valid JSON object. No markdown. No extra text.
Use SPECIFIC vocabulary words, quotes, and questions from the source text above.

{{
  "leading_objective": "Students will ... (activate prior knowledge about the text)",

  "leading_activity": {{
    "number": "01",
    "emoji": "💡",
    "instructions": [
      "Verb + specific instruction related to the text",
      "Verb + specific instruction",
      "Verb + specific instruction"
    ],
    "questions": [
      "Specific question connecting prior knowledge to the text?",
      "Specific question?",
      "Specific question?"
    ]
  }},

  "building_objective": "Students will ... (engage with the text and identify key elements)",

  "before_reading": {{
    "number": "02",
    "emoji": "📖",
    "instructions": [
      "Verb + instruction using actual vocabulary from the text",
      "Verb + instruction"
    ],
    "questions": [
      "Pre-reading question anchored in the text?",
      "Pre-reading question?"
    ]
  }},

  "during_reading": {{
    "number": "03",
    "emoji": "✏️",
    "instructions": [
      "Read + specific section or paragraph reference from the text",
      "Underline/Highlight + what to look for (specific to this text)",
      "Note + specific literary device or character detail from this text",
      "Verb + instruction"
    ],
    "questions": []
  }},

  "after_reading": {{
    "number": "04",
    "emoji": "💬",
    "instructions": [
      "Discuss + specific theme or event from the text",
      "Compare + specific element",
      "Identify + specific literary device used in this text"
    ],
    "questions": [
      "Analytical question about a specific moment in the text?",
      "Question about character, theme, or author's craft?",
      "Essential Question connection: What qualities help us survive / What are milestones on the path to growing up?"
    ]
  }},

  "extra_activity": {{
    "label": "COLLABORATIVE WORK",
    "number": "05",
    "emoji": "🤝",
    "instructions": [
      "Work + collaborative task specific to this text",
      "Share + what to present to the class"
    ],
    "questions": []
  }}
}}

STRICT RULES:
- All text in English.
- Every instruction and question MUST reference specific content from the source text.
- Instructions MUST start with an action verb.
- Objectives MUST start with "Students will".
- Day {day} focus: {day_description}. Calibrate ALL activities to match this day.
  Day 1 = activation and vocabulary. Day 2 = comprehension while reading.
  Day 3 = reflection and summary. Day 4 = close analysis.
  Day 5 = language, craft and grammar focus.
- The Essential Question for Grade 8 is: "What are some milestones on the path to growing up?"
- The Essential Question for Grade 9 is: "What qualities help us survive?"
- Return ONLY raw JSON. No markdown. No commentary.
"""

    raw = _invoke_with_retry(prompt)
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        lesson_json    = json.loads(raw)
        lesson_content = json.dumps(lesson_json, ensure_ascii=False)
    except json.JSONDecodeError:
        print("  ⚠️  Warning: JSON inválido. Guardando como texto plano.")
        lesson_content = raw

    return {
        "lesson_content": lesson_content,
        "steps": state.get("steps", []) + ["literature_drafted"]
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODO 2: Revisión humana — muestra contenido, sugiere mejoras, espera decisión
# ─────────────────────────────────────────────────────────────────────────────

def review_node(state: AgentState):
    """
    Muestra el contenido generado en pantalla, el agente propone mejoras,
    y el profesor decide qué hacer antes de generar el HTML.
    """
    print("\n" + "=" * 55)
    print("   REVISIÓN DE CONTENIDO — PROFESOR")
    print("=" * 55)

    try:
        data = json.loads(state["lesson_content"])
    except (json.JSONDecodeError, KeyError):
        print("⚠️  El contenido no está en formato JSON. Mostrando texto plano.")
        print(state.get("lesson_content", ""))
        input("\nPresiona Enter para continuar de todas formas...")
        return {
            "approved_content": state.get("lesson_content", ""),
            "steps": state.get("steps", []) + ["review_skipped"]
        }

    _print_content(data)

    print("\n" + "-" * 55)
    print("🤖 Analizando contenido y generando sugerencias...")
    print("-" * 55)
    suggestions = _generate_suggestions(state, data)
    print(suggestions)

    print("\n" + "=" * 55)
    print("  ¿QUÉ DESEAS HACER?")
    print("=" * 55)
    print("  [1] Aceptar el contenido tal como está")
    print("  [2] Aplicar las sugerencias del agente")
    print("  [3] Escribir mis propios cambios")
    print("  [4] Aplicar sugerencias del agente + agregar los míos")
    print("-" * 55)

    choice     = input("Tu elección (1/2/3/4): ").strip()
    final_data = data

    if choice == "1":
        print("\n✔ Contenido aceptado sin cambios.")

    elif choice == "2":
        print("\n🤖 Aplicando sugerencias del agente...")
        final_data = _apply_suggestions(state, data, suggestions)
        print("\n── CONTENIDO ACTUALIZADO ──")
        _print_content(final_data)

    elif choice == "3":
        final_data = _manual_edit(data)

    elif choice == "4":
        print("\n🤖 Aplicando sugerencias del agente...")
        final_data = _apply_suggestions(state, data, suggestions)
        print("\n── CONTENIDO CON SUGERENCIAS APLICADAS ──")
        _print_content(final_data)
        print("\nAhora puedes agregar tus propios cambios adicionales:")
        final_data = _manual_edit(final_data)

    else:
        print("Opción no reconocida. Usando contenido original.")

    print("\n✔ Contenido aprobado. Generando HTML...\n")

    return {
        "approved_content": json.dumps(final_data, ensure_ascii=False),
        "steps": state.get("steps", []) + ["review_approved"]
    }


# ── Funciones auxiliares del review_node ─────────────────────────────────────

def _print_content(data: dict):
    """Imprime el JSON de la sesión de forma legible en pantalla."""
    sections = [
        ("LEADING FOR LEARNING",  "leading_objective",  "leading_activity"),
        ("BUILDING UP KNOWLEDGE", "building_objective",  None),
        ("BEFORE READING",        None,                  "before_reading"),
        ("DURING READING",        None,                  "during_reading"),
        ("AFTER READING",         None,                  "after_reading"),
    ]
    for label, obj_key, act_key in sections:
        print(f"\n{'─' * 55}")
        print(f"  ▶ {label}")
        print(f"{'─' * 55}")
        if obj_key and obj_key in data:
            print(f"  OBJECTIVE:\n    {data[obj_key]}")
        if act_key and act_key in data:
            act = data[act_key]
            act_label = (
                f"ACTIVITY {act.get('number', '')}"
                if act.get("label", "").startswith("ACTIVITY")
                else act.get("label", f"ACTIVITY {act.get('number', '')}")
            )
            print(f"\n  {act_label} {act.get('emoji', '')}")
            for i, inst in enumerate(act.get("instructions", []), 1):
                print(f"    {i}. {inst}")
            for i, q in enumerate(act.get("questions", []), 1):
                print(f"    Q{i}. {q}")

    if "extra_activity" in data:
        extra = data["extra_activity"]
        print(f"\n{'─' * 55}")
        print(f"  ▶ {extra.get('label', 'EXTRA ACTIVITY')} {extra.get('emoji', '')}")
        print(f"{'─' * 55}")
        for i, inst in enumerate(extra.get("instructions", []), 1):
            print(f"    {i}. {inst}")
        for i, q in enumerate(extra.get("questions", []), 1):
            print(f"    Q{i}. {q}")


def _generate_suggestions(state: AgentState, data: dict) -> str:
    """El agente revisa el contenido y propone mejoras pedagógicas concretas."""
    prompt = f"""
You are a senior curriculum reviewer for Lord Byron School (Grade {state.get('grade', '9')}).
Review this lesson plan and suggest SPECIFIC improvements.
Reading : {state.get('reading_title', '')}
Topic   : {state.get('topic', '')}

CURRENT LESSON:
{json.dumps(data, indent=2, ensure_ascii=False)}

Provide 3 to 5 concrete suggestions using this format:

SUGGESTION 1 — [section affected]
Current : "..."
Improved: "..."
Reason  : ...

Be specific and pedagogically grounded. Write in English.
"""
    return _invoke_with_retry(prompt).strip()


def _apply_suggestions(state: AgentState, data: dict, suggestions: str) -> dict:
    """Aplica las sugerencias del agente al JSON."""
    prompt = f"""
You are updating a lesson plan JSON based on reviewer suggestions.

ORIGINAL JSON:
{json.dumps(data, indent=2, ensure_ascii=False)}

SUGGESTIONS TO APPLY:
{suggestions}

Apply ALL suggestions and return the updated JSON.
Return ONLY raw JSON. No markdown. No commentary.
"""
    raw = _invoke_with_retry(prompt).replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        print("  ⚠️  No se pudo aplicar sugerencias. Usando original.")
        return data


def _manual_edit(data: dict) -> dict:
    """
    El profesor describe cambios en lenguaje natural con guardrail.
    El LLM los aplica al JSON.
    """
    from guardrail import es_input_valido, es_instruccion_pedagogica

    print("\n" + "─" * 55)
    print("  ✏️  EDICIÓN MANUAL")
    print("─" * 55)
    print("  Describe los cambios en lenguaje natural.")
    print("  Ejemplos:")
    print('  - "En DURING READING agrega una instrucción sobre craving"')
    print('  - "Cambia la pregunta 2 del AFTER READING, hazla más analítica"')
    print('  - "Agrega una actividad EXIT TICKET al final"')
    print("─" * 55)

    changes = input("\nTus cambios: ").strip()

    if not changes:
        print("  Sin cambios registrados.")
        return data

    # Guardrail Nivel 1
    valido, motivo = es_input_valido(changes)
    if not valido:
        print(f"  ⚠️  Input rechazado: {motivo}")
        return data

    # Guardrail Nivel 2
    if not es_instruccion_pedagogica(changes, _invoke_with_retry):
        print("  ⚠️  La instrucción no parece estar relacionada con la sesión de clase.")
        confirmar = input("  ¿Continuar de todas formas? (s/n): ").strip().lower()
        if confirmar != "s":
            return data

    prompt = f"""
Apply these teacher instructions to the lesson plan JSON exactly as requested.
ONLY modify what is explicitly requested. Keep everything else unchanged.

CURRENT JSON:
{json.dumps(data, indent=2, ensure_ascii=False)}

TEACHER INSTRUCTIONS:
{changes}

Return ONLY the updated raw JSON. No markdown. No commentary.
"""
    raw = _invoke_with_retry(prompt).replace("```json", "").replace("```", "").strip()
    try:
        updated = json.loads(raw)
        print("\n  ✔ Cambios aplicados. Contenido actualizado:")
        _print_content(updated)
        return updated
    except json.JSONDecodeError:
        print("  ⚠️  No se pudieron aplicar los cambios. Usando versión anterior.")
        return data


# ─────────────────────────────────────────────────────────────────────────────
# TEMPLATES HTML — Formato Maestro Lord Byron
# ─────────────────────────────────────────────────────────────────────────────

def _session_tag(session_num: str) -> str:
    return (
        '<div style="width:100%; text-align:center;">'
        '<p style="font-family:\'Montserrat\', Arial, sans-serif; margin:0 0 10px 0;">'
        f'<span style="display:inline-block; background:#166C52; color:white; '
        f'padding:5px 16px; border-radius:10px; font-size:36px; font-weight:300; '
        f'letter-spacing:1px;">SESSION {session_num}</span>'
        '</p></div>'
    )

def _reading_title(title: str) -> str:
    return (
        f'<h3 style="text-align:center; color:#166C52; margin:8px 0 6px 0; '
        f'font-size:2rem; font-family:Arial, Helvetica, sans-serif;">'
        f'{title}</h3>'
    )

def _chapter_subtitle(subtitle: str) -> str:
    return (
        f'<h3 style="text-align:center; color:#166C52; margin:0 0 18px 0; '
        f'font-size:1.45rem; font-weight:500; font-family:Arial, Helvetica, sans-serif;">'
        f'{subtitle}</h3>'
    )

def _block_label(label_text: str) -> str:
    return (
        '<p style="font-family:\'Montserrat\', Arial, sans-serif; text-align:left; margin:0 0 18px 0;">'
        f'<span style="display:inline-block; background:#166C52; color:white; '
        f'padding:7px 18px; border-radius:12px; font-size:26px; font-weight:300; '
        f'letter-spacing:1px;">{label_text}</span>'
        '</p>'
    )

def _objective(text: str) -> str:
    if not text.strip().startswith("Students will"):
        text = "Students will " + text.lstrip()
    return (
        '<h3 style="font-family:Arial, Helvetica, sans-serif; color:rgb(255,51,102); '
        'margin:0 0 8px 0; font-size:1.2rem;">OBJECTIVE</h3>'
        f'<p style="font-family:Arial, Helvetica, sans-serif; margin:0 0 18px 0; '
        f'font-size:1.05rem; line-height:1.7;">{text}</p>'
    )

def _activity_label(label_text: str, emoji: str = "📖") -> str:
    return (
        '<p style="margin:0 0 14px 0; text-align:left;">'
        '<span style="display:inline-flex; align-items:center; gap:5px; '
        'background:#3f7a63; color:white; padding:7px 5px; border-radius:18px; '
        'font-family:\'Comic Sans MS\', \'Trebuchet MS\', Arial, sans-serif; '
        'font-size:28px; font-weight:700; letter-spacing:0.5px; line-height:1;">'
        f'{label_text} '
        f'<span style="display:inline-flex; align-items:center; color:white; '
        f'font-size:22px;">{emoji}</span>'
        '</span></p>'
    )

def _instructions(items: list) -> str:
    li_items = ""
    for item in items:
        words = item.split(" ", 1)
        if len(words) == 2:
            li_items += f'<li><strong>{words[0]}</strong> {words[1]}</li>'
        else:
            li_items += f'<li><strong>{item}</strong></li>'
    return (
        '<h3 style="font-family:Arial, Helvetica, sans-serif; color:#3366FF; '
        'margin:0 0 8px 0; font-size:1.15rem;">Instructions:</h3>'
        '<ul style="font-family:Arial, Helvetica, sans-serif; margin:0 0 14px 20px; '
        'padding:0; line-height:1.8; font-size:1rem;">'
        f'{li_items}'
        '</ul>'
    )

def _questions(items: list) -> str:
    if not items:
        return ""
    li_items = "".join(f'<li>{q}</li>' for q in items)
    return (
        '<ul style="font-family:Arial, Helvetica, sans-serif; margin:0 0 0 20px; '
        'padding:0; line-height:1.9; font-size:1rem;">'
        f'{li_items}'
        '</ul>'
    )

def _activity_block(data: dict) -> str:
    number       = data.get("number", "01")
    emoji        = data.get("emoji", "📖")
    label        = data.get("label", f"ACTIVITY {number}")
    if label.startswith("ACTIVITY"):
        label = f"ACTIVITY {number}"
    instructions = data.get("instructions", [])
    questions    = data.get("questions", [])
    html  = _activity_label(label, emoji)
    if instructions:
        html += _instructions(instructions)
    if questions:
        html += _questions(questions)
    return html


# ─────────────────────────────────────────────────────────────────────────────
# NODO 3: Coder — construye el HTML final con templates
# ─────────────────────────────────────────────────────────────────────────────

def coder_node(state: AgentState):
    """
    Construye el HTML institucional usando los templates del Formato Maestro.
    Lee approved_content (revisado por el profesor) o lesson_content como fallback.
    """
    print("[Agente Programador] Ensamblando HTML institucional...")

    session_num   = state.get("session_number", "01")
    reading_title = state.get("reading_title", "READING TITLE")
    chapter_topic = state.get("topic", "Chapter")
    raw_content   = state.get("approved_content") or state.get("lesson_content", "{}")

    try:
        data = json.loads(raw_content)
    except (json.JSONDecodeError, TypeError):
        print("  ⚠️  Contenido no es JSON. Usando LLM como fallback...")
        data = _fallback_llm_structure(raw_content, session_num, reading_title, chapter_topic)

    body = ""
    body += _session_tag(session_num)
    body += _reading_title(reading_title.upper())
    body += _chapter_subtitle(chapter_topic)

    body += _block_label("LEADING FOR LEARNING")
    body += _objective(data.get("leading_objective", "Students will activate prior knowledge."))
    if "leading_activity" in data:
        body += _activity_block(data["leading_activity"])

    body += _block_label("BUILDING UP KNOWLEDGE")
    body += _objective(data.get("building_objective", "Students will identify key concepts."))

    body += _block_label("BEFORE READING")
    if "before_reading" in data:
        body += _activity_block(data["before_reading"])

    body += _block_label("DURING READING")
    if "during_reading" in data:
        body += _activity_block(data["during_reading"])

    body += _block_label("AFTER READING")
    if "after_reading" in data:
        body += _activity_block(data["after_reading"])

    if "extra_activity" in data:
        body += _activity_block(data["extra_activity"])

    html_output = (
        '<div style="max-width:950px; margin:auto;">'
        f'{body}'
        '</div>'
    )

    return {
        "html_code": html_output,
        "steps": state.get("steps", []) + ["coder_final_validated"]
    }


# ─────────────────────────────────────────────────────────────────────────────
# FALLBACK
# ─────────────────────────────────────────────────────────────────────────────

def _fallback_llm_structure(raw_text: str, session_num: str,
                             reading_title: str, topic: str) -> dict:
    prompt = f"""
Convert the following lesson content into a valid JSON object with this exact structure.
No markdown fences. No extra text.

{{
  "leading_objective": "Students will ...",
  "leading_activity": {{
    "number": "01", "emoji": "💡",
    "instructions": ["Verb + instruction"],
    "questions": ["Question?"]
  }},
  "building_objective": "Students will ...",
  "before_reading": {{
    "number": "02", "emoji": "📖",
    "instructions": ["Verb + instruction"],
    "questions": ["Question?"]
  }},
  "during_reading": {{
    "number": "03", "emoji": "✏️",
    "instructions": ["Verb + instruction"],
    "questions": []
  }},
  "after_reading": {{
    "number": "04", "emoji": "💬",
    "instructions": ["Verb + instruction"],
    "questions": ["Question?"]
  }}
}}

LESSON CONTENT:
{raw_text}
"""
    raw = _invoke_with_retry(prompt).replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}
