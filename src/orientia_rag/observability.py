"""Logging structuré (JSONL) + mesure de métriques (durées, tailles) pour ORIENT'IA.

Un seul événement par ligne de log, avec au minimum `event`, `status` et (pour les
blocs chronométrés) `duration_ms`. Pensé pour être relu/agrégé facilement (jq,
recherche par `turn_id`, etc.) sans dépendance externe.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import contextmanager
from contextvars import ContextVar

from . import config

_logger = logging.getLogger("orientia")
_current_turn_id: ContextVar[str | None] = ContextVar("_current_turn_id", default=None)


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
        }
        payload.update(getattr(record, "fields", {}))
        payload.setdefault("event", record.getMessage())
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _ensure_configured() -> None:
    if _logger.handlers:
        return

    config.LOG_DIR.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(config.LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(_JsonFormatter())

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    _logger.addHandler(file_handler)
    _logger.addHandler(console_handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def llm_usage(message) -> dict:
    """Extrait tokens/coût du dernier message d'un tour agent (usage_metadata côté LangChain,
    cost/cost_details côté OpenRouter) — dimension "coût" exigée par le protocole d'évaluation.
    Renvoie un dict vide si l'un ou l'autre n'est pas disponible (provider différent)."""
    usage = getattr(message, "usage_metadata", None) or {}
    meta = getattr(message, "response_metadata", None) or {}
    fields = {}
    if usage:
        fields["input_tokens"] = usage.get("input_tokens")
        fields["output_tokens"] = usage.get("output_tokens")
        fields["total_tokens"] = usage.get("total_tokens")
    if meta.get("cost") is not None:
        fields["cost_usd"] = meta["cost"]
    return fields


def tool_calls_since(messages: list, since: int) -> list[str]:
    """Noms des outils réellement exécutés dans les messages ajoutés depuis l'index
    `since` (les ToolMessage de la réponse d'un agent LangChain) — pour tracer quels
    outils une réponse a mobilisés, exigé par le protocole d'observabilité."""
    names = []
    for msg in messages[since:]:
        if getattr(msg, "type", None) == "tool":
            names.append(getattr(msg, "name", "?"))
    return names


@contextmanager
def turn_context(turn_id: str | None = None):
    """Associe tous les logs émis dans ce bloc (y compris dans les outils appelés
    par l'agent) au même `turn_id`, pour pouvoir corréler un message client avec
    les appels RAG/ML qu'il a déclenchés."""
    turn_id = turn_id or new_id()
    token = _current_turn_id.set(turn_id)
    try:
        yield turn_id
    finally:
        _current_turn_id.reset(token)


def _base_fields(event: str, extra: dict) -> dict:
    fields = {"event": event, "turn_id": _current_turn_id.get()}
    fields.update(extra)
    return fields


def log_event(event: str, level: int = logging.INFO, **fields) -> None:
    """Log un événement structuré ponctuel (pas de durée à mesurer)."""
    _ensure_configured()
    _logger.log(level, event, extra={"fields": _base_fields(event, fields)})


@contextmanager
def timed(event: str, **fields):
    """Chronomètre un bloc et log sa durée en ms à la sortie, succès ou échec.

    Le context manager renvoie un dict mutable : on peut y ajouter des champs
    pendant l'exécution du bloc (ex : nombre de résultats) et ils seront inclus
    dans le log final.

        with timed("ml.predict", serie=serie) as ctx:
            resultats = pipeline.predict(...)
            ctx["n_resultats"] = len(resultats)
    """
    _ensure_configured()
    start = time.perf_counter()
    ctx: dict = {}
    error: Exception | None = None
    try:
        yield ctx
    except Exception as exc:
        error = exc
        raise
    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        payload = _base_fields(event, {**fields, **ctx, "duration_ms": duration_ms})
        if error is not None:
            payload["status"] = "error"
            payload["error"] = f"{type(error).__name__}: {error}"
            _logger.error(event, extra={"fields": payload})
        else:
            payload["status"] = "ok"
            _logger.info(event, extra={"fields": payload})
