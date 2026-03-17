# historial.py
import json
import os
from datetime import datetime

HISTORIAL_FILE = os.path.join(os.path.dirname(__file__), "historial.json")


def _cargar() -> list:
    """Lee el archivo de historial. Si no existe, devuelve lista vacía."""
    if not os.path.exists(HISTORIAL_FILE):
        return []
    with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _guardar(data: list):
    """Escribe el historial en disco."""
    with open(HISTORIAL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def registrar(session_num: str, grade: str, reading_title: str,
              day: str, day_description: str, filename: str):
    """Agrega una entrada nueva al historial."""
    historial = _cargar()
    entrada = {
        "fecha":           datetime.now().strftime("%Y-%m-%d %H:%M"),
        "session":         session_num,
        "grade":           grade,
        "reading":         reading_title,
        "day":             day,
        "day_description": day_description,
        "archivo":         filename,
    }
    historial.append(entrada)
    _guardar(historial)
    print(f"  [✔] Sesión registrada en historial.")


def mostrar():
    """Imprime el historial completo en pantalla."""
    historial = _cargar()
    if not historial:
        print("\n  No hay sesiones registradas aún.")
        return

    print(f"\n{'═'*65}")
    print(f"  HISTORIAL DE SESIONES — {len(historial)} generadas")
    print(f"{'═'*65}")
    print(f"  {'#':<4} {'Fecha':<17} {'Ses.':<5} {'Gr.':<4} {'Día':<4} {'Lectura'}")
    print(f"  {'─'*60}")

    for i, e in enumerate(historial, 1):
        reading_short = e['reading'][:30] + "..." if len(e['reading']) > 30 else e['reading']
        print(f"  {i:<4} {e['fecha']:<17} {e['session']:<5} "
              f"{e['grade']:<4} {e['day']:<4} {reading_short}")

    print(f"{'═'*65}\n")


def ya_generada(grade: str, reading_title: str, day: str) -> bool:
    """
    Devuelve True si ya existe una sesión con ese grado, lectura y día.
    Útil para advertir al profesor antes de generar un duplicado.
    """
    historial = _cargar()
    for e in historial:
        if (e["grade"]   == grade and
            e["reading"] == reading_title and
            e["day"]     == day):
            return True
    return False