from typing import TypedDict, List
 
class AgentState(TypedDict):
    # --- Campos existentes ---
    topic: str
    session_number: str
    reading_title: str
    lesson_content: str
    html_code: str
    steps: List[str]
    # --- Campos nuevos ---
    grade: str        # "8" o "9"
    source_text: str  # texto extraído del PDF
    approved_content: str # contenido final aprobado por el profesor
    day:              str   # ← NUEVO: "1", "2", "3"...
    day_description:  str   # ← NUEVO: descripción del día
    day_focus: str   # ← tipo de contenido del día (vocabulario, texto, análisis...)
