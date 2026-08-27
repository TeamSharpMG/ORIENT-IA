"""Configuration : variables d'environnement et paramètres du RAG."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PACKAGE_DIR = Path(__file__).resolve().parent
DOCUMENTS_DIR = PACKAGE_DIR / "documents"

LLM_PROVIDER = os.environ["LLM_PROVIDER"]
LLM_MODEL = os.environ["LLM_MODEL"]
LLM_API_TOKEN = os.environ["LLM_API_TOKEN"]

# Paramètres de chunking.
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Nombre de chunks renvoyés par une recherche.
RETRIEVER_K = 4

# ML : recommandation de filières (voir src/orientia_ml/README.md).
ML_PIPELINE_PATH = PACKAGE_DIR.parent / "orientia_ml" / "model" / "orientia_pipeline.joblib"
ML_TOP_K = 3

# Logs structurés (métriques de durée, tailles de réponse, etc.).
LOG_DIR = PACKAGE_DIR.parent.parent / "logs"
LOG_FILE = LOG_DIR / "orientia.jsonl"

# UI : page de test servie par l'API (voir src/orientia_app/).
UI_DIR = PACKAGE_DIR.parent / "orientia_app"

# Adresse d'écoute par défaut pour `orientia-app` (voir src/orientia_app/__init__.py).
API_HOST = os.environ.get("API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("API_PORT", "8000"))
