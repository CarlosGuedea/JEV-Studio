# Jev Studio

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-apóyame-ffdd00?logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/carlosguedea)

Editor visual para crear, conectar y ejecutar flujos de inteligencia artificial donde **Jev** (el modelo de decisiones tipadas de TypeSafe AI) funciona como motor de decisión, combinado con LLMs, APIs REST, Python y otras herramientas. Inspirado en Node-RED / n8n / Langflow.

![Stack](https://img.shields.io/badge/stack-React%20%C2%B7%20TypeScript%20%C2%B7%20Vite%20%C2%B7%20React%20Flow%20%C2%B7%20FastAPI%20%C2%B7%20SQLite-7c3aed)

## Qué incluye

- **Editor visual** (React Flow): arrastrar y soltar nodos, conexiones, zoom, minimapa, grid, duplicar/eliminar nodos, modo claro/oscuro.
- **Motor de ejecución real** en el backend: validación del grafo, orden topológico, ramificaciones por decisión, detección de errores, límite anti-ciclos y registro de cada paso.
- **Nodos**: `Input`, `Jev Decision`, `LLM`, `Python` (seguro), `HTTP Request`, `Condition`, `Output`.
- **Integración con Jev**: `TypeSafeJevProvider` contra la API oficial (`POST /v1/systemone`) y `MockJevProvider` claramente etiquetado como simulación cuando no hay API key.
- **Persistencia** en SQLite (Workflow, Node, Edge, Execution, ExecutionStep).
- **API REST** completa + pruebas (`pytest`), Dockerfiles y `docker-compose.yml`.

## Arquitectura

```
frontend/   React + TypeScript + Vite + Tailwind + React Flow (editor, paneles, store zustand)
backend/
  app/
    api/         endpoints REST (workflows, executions, providers)
    engine/      validación del grafo + runner de ejecución con ramas
    nodes/       ejecutores por tipo de nodo (registro extensible)
    providers/   JevProvider (TypeSafe / Mock) y proveedores LLM
    models/      modelos SQLAlchemy (SQLite)
    schemas/     modelos Pydantic (contrato JSON con el frontend)
    services/    CRUD de workflows, ejecuciones, semilla demo
```

El frontend envía al backend un JSON `{nodes, edges, config, variables}`; el backend lo valida, ejecuta y devuelve el estado de cada nodo (`IDLE / QUEUED / RUNNING / SUCCESS / ERROR / SKIPPED`) junto con entrada, salida, tiempo y error por nodo.

## Instalación y ejecución

### Opción A — Docker (recomendada)

```bash
cp .env.example .env   # rellena TYPESAFE_API_KEY si tienes una
docker compose up --build
```

Abre http://localhost:7100 (frontend) · API en http://localhost:8155.

### Opción B — Local

Requisitos: Node 20+, Python 3.11+.

```bash
# Backend
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env   # opcional
uvicorn app.main:app --reload --port 8155

# Frontend (otra terminal)
cd frontend
npm install
npm run dev -- --port 7100
```

O ambos a la vez desde la raíz del proyecto: `npm install && npm run dev`.

### Pruebas

```bash
cd backend && python3 -m pytest tests -q     # 21 pruebas
```

Cubren: validación del grafo, ejecución lineal, ramificaciones, propagación de errores, `Condition`, `MockJevProvider` y el formato de wire de `TypeSafeJevProvider` (sin llamadas externas reales).

## Configuración

Toda la configuración es por variables de entorno (ver `.env.example`):

| Variable | Descripción |
|---|---|
| `TYPESAFE_API_KEY` / `JEV_API_KEY` | Key de la API oficial de TypeSafe. Sin ella, Jev Studio usa el mock de desarrollo. |
| `OPENAI_API_KEY` / `OPENAI_BASE_URL` | Para el nodo LLM (OpenAI o cualquier endpoint compatible: llama.cpp, vLLM, LM Studio…). |
| `HTTP_ALLOWED_HOSTS` | Allowlist de hosts para el nodo HTTP Request (vacío = todos). |
| `DATABASE_URL` | SQLite por defecto. |

**Nunca se almacenan API keys dentro del JSON del workflow**: el nodo LLM solo referencia el *nombre* de la variable de entorno (`api_key_env`), y el secreto se resuelve en el servidor en tiempo de ejecución.

## API REST

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/workflows` | Listar workflows |
| POST | `/api/workflows` | Crear (recibe `definition`) |
| GET | `/api/workflows/{id}` | Obtener uno |
| PUT | `/api/workflows/{id}` | Actualizar |
| DELETE | `/api/workflows/{id}` | Eliminar |
| POST | `/api/workflows/{id}/duplicate` | Duplicar |
| POST | `/api/workflows/{id}/execute` | Ejecutar (`{input, variables}`) |
| GET | `/api/executions/{id}` | Estado de una ejecución |
| GET | `/api/executions/{id}/steps` | Pasos de una ejecución |
| GET | `/api/providers` | Proveedores activos (Jev real vs mock) |

## Cómo crear un nodo nuevo

1. **Backend** — en `backend/app/nodes/executors.py` crea una clase que herede de `NodeExecutor`, implementa `execute(ctx)` (devuelve un dict JSON-serializable; opcionalmente `branch(ctx, result)` para nodos con ramas) y regístrala en `_REGISTRY`.
2. **Schema** — añade su config en `backend/app/schemas/workflow.py` y al union `NodeConfig`.
3. **Frontend** — añade sus campos por defecto en `src/types/workflow.ts` (`DEFAULT_CONFIGS`), su componente visual en `src/nodes/`, y sus campos de edición en `src/components/InspectorPanel.tsx`.

## Cómo integrar Jev

`backend/app/providers/jev_base.py` define la abstracción:

```python
class JevProvider(ABC):
    def decide(self, context: str, question: str, options: list[str]) -> JevDecision: ...
```

- `TypeSafeJevProvider` adapta esa interfaz a la API oficial: `POST {base_url}/v1/systemone` con body `{state, questions, model}` y una pregunta de tipo `choice` cuyos criterios son las opciones; la respuesta llega en `answers[key].choice` con `confidence` calibrada.
- `MockJevProvider` es una simulación determinista (heurística de palabras clave) marcada con `simulated=True` para desarrollo sin key.
- El modo por nodo se elige en el inspector del nodo: `auto` (real si hay key, si no mock), `typesafe` o `mock`.

## Cómo agregar nuevos proveedores LLM

Implementa `LLMProvider.chat(...)` en `backend/app/providers/llm.py` y regístralo en `registry()`. El `OpenAICompatibleProvider` existente ya cubre OpenAI y cualquier servidor compatible (llama.cpp, vLLM, LM Studio) cambiando solo `endpoint`/`model`.

## Seguridad

- Validación de todos los inputs con Pydantic.
- El nodo **Python** no usa `exec`: evalúa expresiones con un AST de lista blanca (sin imports, ni atributos, ni llamadas fuera de lista).
- Nodo **HTTP Request**: solo `http/https`, allowlist opcional de hosts, timeout y límite de tamaño de respuesta.
- Nodo **LLM**: timeout y límite de tamaño de respuesta; la key se lee del entorno.
- El motor detiene ejecuciones que superen `ENGINE_MAX_STEPS` pasos (anti-ciclos).

## Workflow de demostración

Al arrancar con la base de datos vacía se siembra “Demo: Clasificador Jev”:

```
User Input → Jev Decision (SQL/PYTHON/LLM/RAG/REJECT)
               ├─ SQL    → HTTP Request      ┐
               ├─ PYTHON → Python            ├→ Jev Evaluator (ACCEPT/REJECT) → Output
               ├─ LLM    → LLM               ┘
               └─ REJECT → Output
```

Con el mock activo, escribe entradas como *“cuenta palabras con python”* o *“haz un resumen con LLM”* (esta última requiere `OPENAI_API_KEY`) para ver la ramificación en acción.

## Apoya el proyecto

Si Jev Studio te resulta útil, puedes invitarme a un café:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-buymeacoffee.com%2Fcarlosguedea-ffdd00?logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/carlosguedea)

Todo el aporte se destina a tiempo de desarrollo y tokens de API para seguir mejorando la herramienta.
