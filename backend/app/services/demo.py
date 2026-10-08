"""Demo workflow seed — clasificador + evaluador.

User Input → Jev Decision (SQL / PYTHON / LLM / RAG / REJECT)
                ├─ SQL    → HTTP (API simulada) → Jev Evaluator
                ├─ PYTHON → Python (contar palabras) → Jev Evaluator
                ├─ LLM    → LLM (responde) → Jev Evaluator
                └─ REJECT → Output
Jev Evaluator (ACCEPT / REJECT) → Output
"""
from ..schemas import WorkflowDefinition

DEMO_WORKFLOW = {
    "config": {
        "name": "Demo: Clasificador Jev",
        "description": "Clasifica la solicitud con Jev, procesa por la rama elegida y evalúa la respuesta.",
    },
    "variables": {},
    "nodes": [
        {"id": "n_input", "type": "input", "label": "User Input",
         "position": {"x": 0, "y": 260}, "config": {"message": "Describe tu solicitud"}},
        {"id": "n_router", "type": "jev_decision", "label": "Jev · Clasificador",
         "position": {"x": 260, "y": 260},
         "config": {"name": "Clasificador",
                    "instructions": "Clasifica la solicitud del usuario en la mejor ruta de procesamiento.",
                    "question": "¿Qué ruta debe procesar esta solicitud?",
                    "options": ["SQL", "PYTHON", "LLM", "RAG", "REJECT"]}},
        {"id": "n_sql", "type": "http_request", "label": "HTTP · SQL API",
         "position": {"x": 560, "y": 60},
         "config": {"url": "https://jsonplaceholder.typicode.com/posts/1",
                    "method": "GET", "headers": {}, "body": None, "timeout_seconds": 15}},
        {"id": "n_py", "type": "python", "label": "Python · Análisis",
         "position": {"x": 560, "y": 200},
         "config": {"expression": "len(split(input))", "description": "Cuenta palabras de la solicitud"}},
        {"id": "n_llm", "type": "llm", "label": "LLM · Respuesta",
         "position": {"x": 560, "y": 340},
         "config": {"provider": "openai", "endpoint": "", "model": "gpt-4o-mini",
                    "api_key_env": "OPENAI_API_KEY",
                    "system_prompt": "Eres un asistente útil y conciso.",
                    "prompt": "Responde a la siguiente solicitud: {{input}}",
                    "temperature": 0.7, "max_tokens": 512}},
        {"id": "n_eval", "type": "jev_decision", "label": "Jev · Evaluador",
         "position": {"x": 860, "y": 200},
         "config": {"name": "Evaluador",
                    "instructions": "Evalúa si la respuesta obtenida es aceptable para la solicitud.",
                    "question": "¿La respuesta es aceptable?",
                    "options": ["ACCEPT", "REJECT"]}},
        {"id": "n_out_ok", "type": "output", "label": "Output · Aceptado",
         "position": {"x": 1180, "y": 120}, "config": {"label": "Resultado aceptado"}},
        {"id": "n_out_reject", "type": "output", "label": "Output · Rechazado",
         "position": {"x": 1180, "y": 300}, "config": {"label": "Resultado rechazado"}},
    ],
    "edges": [
        {"id": "e1", "source": "n_input", "target": "n_router", "label": None},
        {"id": "e_sql", "source": "n_router", "target": "n_sql", "label": "SQL"},
        {"id": "e_py", "source": "n_router", "target": "n_py", "label": "PYTHON"},
        {"id": "e_llm", "source": "n_router", "target": "n_llm", "label": "LLM"},
        {"id": "e_rej", "source": "n_router", "target": "n_out_reject", "label": "REJECT"},
        {"id": "e_sql2", "source": "n_sql", "target": "n_eval", "label": None},
        {"id": "e_py2", "source": "n_py", "target": "n_eval", "label": None},
        {"id": "e_llm2", "source": "n_llm", "target": "n_eval", "label": None},
        {"id": "e_acc", "source": "n_eval", "target": "n_out_ok", "label": "ACCEPT"},
        {"id": "e_rej2", "source": "n_eval", "target": "n_out_reject", "label": "REJECT"},
    ],
}


def demo_definition() -> WorkflowDefinition:
    return WorkflowDefinition.model_validate(DEMO_WORKFLOW)


def seed_demo(db) -> None:
    from ..models import Workflow
    from .workflow_service import create_workflow

    if db.query(Workflow).count() == 0:
        create_workflow(db, demo_definition())
