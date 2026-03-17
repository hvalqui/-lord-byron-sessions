from langgraph.graph import StateGraph, END
from estado import AgentState
from nodos import literature_professor_node, review_node, coder_node

# ─────────────────────────────────────────────────────────────────────────────
# GRAFO 1: TERMINAL — incluye review_node interactivo (input() en consola)
# Usado por: ejecutar_agente.py
# ─────────────────────────────────────────────────────────────────────────────
workflow = StateGraph(AgentState)
workflow.add_node("profesor",    literature_professor_node)
workflow.add_node("revision",    review_node)
workflow.add_node("programador", coder_node)
workflow.set_entry_point("profesor")
workflow.add_edge("profesor",    "revision")
workflow.add_edge("revision",    "programador")
workflow.add_edge("programador", END)

app = workflow.compile()

# ─────────────────────────────────────────────────────────────────────────────
# GRAFO 2: DASHBOARD — sin review_node (la revisión ocurre en Streamlit)
# Usado por: app.py
# ─────────────────────────────────────────────────────────────────────────────
workflow_web = StateGraph(AgentState)
workflow_web.add_node("profesor",    literature_professor_node)
workflow_web.add_node("programador", coder_node)
workflow_web.set_entry_point("profesor")
workflow_web.add_edge("profesor",    "programador")
workflow_web.add_edge("programador", END)

app_web = workflow_web.compile()