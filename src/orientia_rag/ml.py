"""Recommandation ML de filières (top-3) + décomposition du score pour l'explicabilité.

Enveloppe orientia_ml.orientia_pipeline.OrientiaPipeline. On recalcule ici la
combinaison faite par `OrientiaPipeline.predict()` à partir d'un seul appel à
`score_components()` plutôt que d'appeler predict() et score_components()
séparément (chacun encode le profil avec le modèle d'embeddings : appeler les
deux ferait tourner l'embedding deux fois pour rien).
"""

from __future__ import annotations

import unicodedata
from functools import lru_cache
from typing import Iterable

import numpy as np
from orientia_ml.orientia_pipeline import OrientiaPipeline, eligibilite_serie

from . import config
from .observability import timed

RIASEC_LABELS = {
    "R": "Réaliste",
    "I": "Investigateur",
    "A": "Artistique",
    "S": "Social",
    "E": "Entreprenant",
    "C": "Conventionnel",
}

_RIASEC_WORDS = {
    unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode().lower(): letter
    for letter, label in RIASEC_LABELS.items()
}


def normalize_riasec_letters(letters: Iterable[str]) -> set[str]:
    """Accepte des lettres RIASEC ('I', 'R', ...) ou les mots correspondants
    ('Investigateur', 'investigateur', accents ou non) et renvoie l'ensemble des
    lettres reconnues. Les entrées non reconnues sont simplement ignorées."""
    normalized: set[str] = set()
    for raw in letters:
        token = (raw or "").strip()
        if not token:
            continue
        if token.upper() in RIASEC_LABELS:
            normalized.add(token.upper())
            continue
        ascii_token = unicodedata.normalize("NFKD", token).encode("ascii", "ignore").decode().lower()
        if ascii_token in _RIASEC_WORDS:
            normalized.add(_RIASEC_WORDS[ascii_token])
    return normalized


@lru_cache(maxsize=1)
def _get_pipeline() -> OrientiaPipeline:
    with timed("ml.load_pipeline", path=str(config.ML_PIPELINE_PATH)):
        return OrientiaPipeline.load(str(config.ML_PIPELINE_PATH))


def warm_up() -> None:
    """Précharge le pipeline (modèle d'embeddings inclus) pour éviter que le
    premier message d'un utilisateur ne paie le coût de chargement à froid."""
    _get_pipeline()


def recommend_filieres(
    serie: str,
    matiere: str,
    interets: str,
    caractere_letters: Iterable[str],
    top_k: int = config.ML_TOP_K,
) -> list[dict]:
    """Top-k filières recommandées, chacune avec sa décomposition de score
    (similarité intérêts, correspondance personnalité, éligibilité de la série)."""
    pipeline = _get_pipeline()
    letters = normalize_riasec_letters(caractere_letters)

    with timed(
        "ml.predict",
        serie=serie,
        matiere=matiere,
        interets=interets,
        traits=sorted(letters),
        top_k=top_k,
    ) as ctx:
        sim_content, sim_riasec, elig = pipeline.score_components(serie, matiere, interets, letters)
        score = (pipeline.w_content * sim_content + pipeline.w_riasec * sim_riasec) * elig
        total = score.sum()
        proba = score / total if total > 0 else np.ones(len(pipeline.filieres)) / len(pipeline.filieres)

        top_idx = sorted(range(len(pipeline.filieres)), key=lambda i: proba[i], reverse=True)[:top_k]

        resultats = [
            {
                "code": pipeline.filieres[i]["code"],
                "nom": pipeline.filieres[i]["nom"],
                "departement": pipeline.filieres[i]["departement"],
                "pourcentage": round(float(100 * proba[i]), 1),
                "explication": {
                    "similarite_interets": round(float(sim_content[i]), 3),
                    "correspondance_personnalite": round(float(sim_riasec[i]), 3),
                    "eligibilite_serie": float(elig[i]),
                },
            }
            for i in top_idx
        ]

        ctx["resultats"] = [{"code": r["code"], "pourcentage": r["pourcentage"]} for r in resultats]

    return resultats


def verifier_eligibilite(serie: str, code_filiere: str) -> dict | None:
    """Score d'éligibilité heuristique entre une série de bac et UNE filière précise
    (désignée par son code, ex: "ISAIA"). Réutilise directement eligibilite_serie() du
    pipeline ML — ce n'est PAS une règle d'admission officielle, juste la même pondération
    de recommandation que celle utilisée dans recommend_filieres(), isolée pour une
    filière donnée. Renvoie None si le code ne correspond à aucune filière connue."""
    pipeline = _get_pipeline()

    with timed("ml.verifier_eligibilite", serie=serie, code_filiere=code_filiere) as ctx:
        filiere = next((f for f in pipeline.filieres if f["code"].upper() == code_filiere.strip().upper()), None)
        if filiere is None:
            ctx["trouve"] = False
            return None

        score = eligibilite_serie(serie, filiere["departement"], pipeline.dept_series)
        ctx["trouve"] = True
        ctx["score"] = score

    return {
        "code": filiere["code"],
        "nom": filiere["nom"],
        "departement": filiere["departement"],
        "score_eligibilite": score,
    }
