# guardrail.py
# Validación de inputs del profesor — dos niveles de protección

TEMAS_VALIDOS = [
    # Inglés — pedagógico
    "reading", "chapter", "story", "lesson", "vocabulary", "activity",
    "objective", "question", "instruction", "grammar", "theme", "plot",
    "character", "analysis", "writing", "discussion", "comprehension",
    "before", "during", "after", "leading", "building", "collaborative",
    "student", "teacher", "text", "paragraph", "author", "literary",
    "fiction", "nonfiction", "poetry", "narrative", "argument", "summary",
    "metaphor", "simile", "symbol", "conflict", "setting", "mood", "tone",
    "inference", "prediction", "annotation", "close read", "exit ticket",
    "forum", "metacognition", "skill", "standard", "essential question",
    "quote", "passage", "excerpt", "scene", "dialogue", "point of view",
    "first person", "third person", "diction", "syntax", "imagery",
    "foreshadowing", "flashback", "irony", "alliteration", "personification",
    # Español — instrucciones del profesor
    "lectura", "capítulo", "historia", "lección", "vocabulario", "actividad",
    "objetivo", "pregunta", "instrucción", "gramática", "tema", "trama",
    "personaje", "análisis", "escritura", "discusión", "comprensión",
    "estudiante", "profesor", "texto", "párrafo", "autor", "literario",
    "cambio", "agrega", "modifica", "reemplaza", "añade", "elimina",
    "cambia", "mejora", "actualiza", "quita", "pon", "incluye", "usa",
    "sesión", "clase", "actividad", "ejercicio", "tarea", "evaluación",
    "before reading", "during reading", "after reading",
    "leading for learning", "building up knowledge",
]

TEMAS_INVALIDOS = [
    # Contenido claramente fuera del proyecto
    "joke", "chiste", "funny", "gracioso", "humor",
    "recipe", "receta", "cook", "cocinar", "food", "comida",
    "weather", "clima", "forecast", "pronóstico",
    "sport", "deporte", "football", "soccer", "basketball",
    "game", "juego", "videogame", "videojuego",
    "movie", "película", "netflix", "series", "show",
    "music", "música", "song", "canción", "playlist",
    "politics", "política", "election", "elección", "president",
    "religion", "religión", "church", "iglesia",
    "investment", "inversión", "stock", "crypto", "bitcoin",
    "dating", "citas", "relationship", "pareja",
    "diet", "dieta", "exercise", "ejercicio físico", "gym",
    "horoscope", "horóscopo", "astrology", "astrología",
]


def es_input_valido(texto: str) -> tuple:
    """
    Nivel 1: Validación rápida por keywords — sin costo de API.
    Devuelve (True, "") si el input es válido.
    Devuelve (False, motivo) si no lo es.
    """
    if not texto or not texto.strip():
        return False, "El campo no puede estar vacío."

    texto_lower = texto.lower().strip()

    # Muy corto
    if len(texto_lower) < 3:
        return False, "El texto es demasiado corto."

    # Contiene temas explícitamente inválidos
    for tema in TEMAS_INVALIDOS:
        if tema in texto_lower:
            return False, (
                f"El contenido '{tema}' no está relacionado con el proyecto. "
                f"Por favor ingresa instrucciones sobre la sesión de clase."
            )

    # Contiene al menos una palabra clave válida → aprobado
    for tema in TEMAS_VALIDOS:
        if tema in texto_lower:
            return True, ""

    # Sin keywords pero sin temas inválidos →
    # puede ser un título de capítulo legítimo (ej: "The Rocky Bay")
    # Lo dejamos pasar — el Nivel 2 lo verificará si es necesario
    return True, ""


def es_instruccion_pedagogica(texto: str, invoke_fn) -> bool:
    """
    Nivel 2: Validación inteligente con el LLM.
    Solo se usa para cambios manuales complejos.
    invoke_fn debe ser la función _invoke_with_retry de nodos.py.
    """
    prompt = f"""
You are a content moderator for an English Literature lesson generator 
used by a teacher at Lord Byron School.

Determine if the following teacher instruction is related to:
- Lesson planning for English Literature
- Reading activities, vocabulary, literary analysis
- Classroom activities, objectives, or student tasks
- Modifying or improving a lesson plan

Instruction: "{texto}"

Reply with only one word: YES or NO.
"""
    try:
        respuesta = invoke_fn(prompt).strip().upper()
        return respuesta.startswith("YES")
    except Exception:
        # Si falla la validación, dejamos pasar para no bloquear al profesor
        return True
