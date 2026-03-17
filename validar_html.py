# validar_html.py

# Secciones que SIEMPRE deben estar presentes en el HTML final
SECCIONES_OBLIGATORIAS = [
    ("SESSION",               "Etiqueta SESSION"),
    ("LEADING FOR LEARNING",  "Bloque LEADING FOR LEARNING"),
    ("BUILDING UP KNOWLEDGE", "Bloque BUILDING UP KNOWLEDGE"),
    ("BEFORE READING",        "Bloque BEFORE READING"),
    ("DURING READING",        "Bloque DURING READING"),
    ("AFTER READING",         "Bloque AFTER READING"),
    ("OBJECTIVE",             "Al menos un OBJECTIVE"),
    ("Instructions:",         "Al menos un bloque de instrucciones"),
    ("#166C52",               "Color verde principal"),
    ("#3f7a63",               "Color verde secundario"),
    ("rgb(255,51,102)",       "Color rosa para OBJECTIVE"),
    ("#3366FF",               "Color azul para Instructions"),
]

def validar(html: str) -> tuple[bool, list]:
    """
    Verifica que el HTML contenga todas las secciones obligatorias.
    Devuelve (True, []) si todo está bien.
    Devuelve (False, [lista de errores]) si falta algo.
    """
    errores = []

    for token, descripcion in SECCIONES_OBLIGATORIAS:
        if token not in html:
            errores.append(f"  ✘ Falta: {descripcion} ({token})")

    return (len(errores) == 0), errores