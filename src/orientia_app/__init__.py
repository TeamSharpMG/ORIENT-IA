"""Point d'entrée de l'application web ORIENT'IA (API + interface de test).

Ce package regroupe ce qui sert à *lancer* l'app : la page de test (index.html,
servie par orientia_rag.api) et la commande `orientia-app` qui démarre le
serveur. Toute la logique (agent, RAG, ML, routes) vit dans orientia_rag.
"""

import uvicorn

from orientia_rag import config


def main() -> None:
    uvicorn.run("orientia_rag.api:app", host=config.API_HOST, port=config.API_PORT)


__all__ = ["main"]
