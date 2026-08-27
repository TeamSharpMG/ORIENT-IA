"""API HTTP : soumission du profil ML puis poursuite de la discussion avec l'agent.

Deux étapes :
- `POST /sessions` crée une session à partir du profil élève (série, matière préférée,
  intérêts, traits RIASEC) : l'agent y répond en s'appuyant sur l'outil `recommend_filieres`
  exactement comme dans le CLI (voir agent.py).
- `POST /sessions/{session_id}/messages` continue ensuite la discussion normalement, avec
  le même agent (RAG + ML) et l'historique complet de la session.

Lancer : `uv run orientia-app` (ou `uv run uvicorn orientia_rag.api:app --reload` en dev) puis voir /docs.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from . import config
from .agent import build_agent
from .observability import llm_usage, log_event, new_id, timed, tool_calls_since, turn_context

_sessions: dict[str, list] = {}
_agent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _agent
    with timed("api.startup"):
        _agent = build_agent()
    log_event("api.ready")
    yield
    log_event("api.shutdown")


app = FastAPI(title="ORIENT'IA API", lifespan=lifespan)


class ProfilInput(BaseModel):
    serie_bac: str
    matiere_preferee: str
    interets: str
    traits_personnalite: list[str] = Field(
        default_factory=list,
        description="Sous-ensemble de R, I, A, S, E, C (RIASEC), lettres ou mots complets.",
    )


class MessageInput(BaseModel):
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str


@app.middleware("http")
async def log_requests(request, call_next):
    with timed("api.request", method=request.method, path=request.url.path) as ctx:
        response = await call_next(request)
        ctx["status_code"] = response.status_code
    return response


def _format_profile_message(profil: ProfilInput) -> str:
    traits = ", ".join(profil.traits_personnalite) or "non précisé"
    return (
        f"Mon profil : série de bac {profil.serie_bac}, matière préférée : {profil.matiere_preferee}, "
        f"centres d'intérêt : {profil.interets}, traits de personnalité (RIASEC) : {traits}. "
        f"Peux-tu me conseiller des filières adaptées ?"
    )


def _run_turn(session_id: str, event: str, messages: list) -> list:
    n_before = len(messages)
    with turn_context():
        with timed(
            event,
            session_id=session_id,
            question=messages[-1]["content"],
        ) as ctx:
            result = _agent.invoke({"messages": messages})
            ctx["reponse_finale"] = result["messages"][-1].content
            ctx["outils_appeles"] = tool_calls_since(result["messages"], n_before)
            ctx.update(llm_usage(result["messages"][-1]))
    return result["messages"]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index():
    """Petite page de test manuelle : formulaire de profil puis chat, via /sessions."""
    return (config.UI_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/logo.png", include_in_schema=False)
def logo():
    return FileResponse(config.UI_DIR / "logo.png", media_type="image/png")


@app.post("/sessions", response_model=ChatResponse, status_code=201)
def start_session(profil: ProfilInput):
    """Reçoit le profil (l'input nécessaire au ML), lance le premier tour d'agent,
    puis ouvre une session que le client peut poursuivre via /sessions/{id}/messages."""
    session_id = new_id()
    log_event("api.profil_construit", session_id=session_id, profil=profil.model_dump())
    question = _format_profile_message(profil)
    messages = _run_turn(session_id, "api.start_session", [{"role": "user", "content": question}])
    _sessions[session_id] = messages
    return ChatResponse(session_id=session_id, reply=messages[-1].content)


@app.post("/sessions/{session_id}/messages", response_model=ChatResponse)
def continue_session(session_id: str, payload: MessageInput):
    history = _sessions.get(session_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Session inconnue")

    messages = history + [{"role": "user", "content": payload.message}]
    messages = _run_turn(session_id, "api.chat_message", messages)
    _sessions[session_id] = messages
    return ChatResponse(session_id=session_id, reply=messages[-1].content)
