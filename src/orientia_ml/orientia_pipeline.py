"""Module d'inférence ORIENT'IA — à importer tel quel dans une app (API, script, etc.).

Ne dépend PAS des données brutes (Sondage.csv / riasec.csv) : uniquement du fichier
model/orientia_pipeline.joblib (déjà entraîné et calibré) et du modèle d'embeddings
SentenceTransformer (téléchargé/mis en cache automatiquement au premier appel).

Usage minimal :

    from orientia_pipeline import OrientiaPipeline

    pipeline = OrientiaPipeline.load("model/orientia_pipeline.joblib")
    resultats = pipeline.predict(
        serie="D",
        matiere="Mathématiques",
        interets="jeux vidéo, robotique, programmation",
        caractere_letters={"I", "R"},
        top_k=5,
    )
    # -> [{"code": "ISAIA", "nom": "...", "departement": "...", "pourcentage": 14.0}, ...]
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

import joblib
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def normalize_0_1(x):
    x = np.asarray(x, dtype=float)
    lo, hi = x.min(), x.max()
    if hi - lo < 1e-9:
        return np.ones_like(x) / len(x)
    return (x - lo) / (hi - lo)


def riasec_letters_to_vector(letters: Iterable[str], selected_score: float = 4.0, baseline: float = 2.0):
    """Convertit un sous-ensemble de lettres RIASEC sélectionnées en vecteur 6-dim
    sur la même échelle (1-5) que les scores moyens du dataset externe utilisé à l'entraînement."""
    letters = set(letters)
    return np.array([selected_score if l in letters else baseline for l in "RIASEC"])


def eligibilite_serie(bac_serie: str, dept_name: str, dept_series: dict) -> float:
    """Score d'éligibilité souple (1.0 = série listée, 0.6 = partiellement incertain,
    0.4 = incertain/non listé). Ce n'est PAS une règle d'admission stricte, juste une
    pondération pour la recommandation — ne pas l'utiliser pour décider d'une admission réelle."""
    txt = dept_series.get(dept_name, "").lower()
    if "toutes séries" in txt or "toutes series" in txt:
        return 1.0
    s = bac_serie.strip().upper()
    s_low = bac_serie.strip().lower()
    if s in ("C", "D", "S") and re.search(rf"\b{s}\b", dept_series.get(dept_name, "")):
        return 1.0
    if s == "TGI" and "technique" in txt and "industr" in txt:
        return 1.0
    if "technique" in s_low and "agricol" in s_low and "agricol" in txt:
        return 1.0
    if "technique" in s_low and "civil" in s_low and "civil" in txt:
        return 1.0
    if s == "A2" and "a2" in txt:
        return 1.0
    if s.startswith("A") and "a2" in txt:
        return 0.6
    return 0.4


@dataclass
class OrientiaPipeline:
    riasec_clf: object
    dept_order: list
    filieres: list
    filiere_embeddings: np.ndarray
    dept_series: dict
    w_content: float
    w_riasec: float
    embed_model: object

    @classmethod
    def load(cls, joblib_path: str, embed_model=None):
        """Charge le pipeline depuis le .joblib. Le modèle d'embeddings est chargé
        séparément (lazy) car il n'est pas sérialisé dans le .joblib — il se
        re-télécharge/récupère depuis le cache HuggingFace automatiquement."""
        d = joblib.load(joblib_path)
        if embed_model is None:
            from sentence_transformers import SentenceTransformer

            embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        return cls(
            riasec_clf=d["riasec_clf"],
            dept_order=d["dept_order"],
            filieres=d["filieres"],
            filiere_embeddings=d["filiere_embeddings"],
            dept_series=d["dept_series"],
            w_content=d["w_content"],
            w_riasec=d["w_riasec"],
            embed_model=embed_model,
        )

    def _filiere_depts(self):
        return np.array([f["departement"] for f in self.filieres])

    def score_components(self, serie: str, matiere: str, interets: str, caractere_letters: Iterable[str]):
        """Calcule séparément les 3 composantes du score (similarité de contenu, similarité
        RIASEC redistribuée par filière, éligibilité), sans les combiner. Utile pour du debug
        ou pour re-calibrer w_content/w_riasec sur de nouvelles données."""
        filiere_depts = self._filiere_depts()

        profil_txt = (
            f"J'aime {matiere}. Mes centres d'intérêt : {interets}. "
            f"Traits de personnalité : {', '.join(sorted(caractere_letters)) or 'non précisé'}."
        )
        profil_emb = self.embed_model.encode([profil_txt], normalize_embeddings=True)
        sim_content = cosine_similarity(profil_emb, self.filiere_embeddings)[0]
        sim_content_norm = normalize_0_1(sim_content)

        riasec_vec = riasec_letters_to_vector(caractere_letters).reshape(1, -1)
        dept_proba = dict(zip(self.dept_order, self.riasec_clf.predict_proba(riasec_vec)[0]))

        sim_riasec = np.zeros(len(self.filieres))
        for dept in set(filiere_depts):
            idx = np.where(filiere_depts == dept)[0]
            p_dept = dept_proba.get(dept, 0.0)
            share = normalize_0_1(sim_content[idx])
            share = share / share.sum() if share.sum() > 0 else np.ones(len(idx)) / len(idx)
            sim_riasec[idx] = p_dept * share

        elig = np.array([eligibilite_serie(serie, f["departement"], self.dept_series) for f in self.filieres])

        return sim_content_norm, sim_riasec, elig

    def predict(
        self,
        serie: str,
        matiere: str,
        interets: str,
        caractere_letters: Iterable[str],
        top_k: int = 5,
        w_content: float | None = None,
        w_riasec: float | None = None,
    ):
        """Retourne le top-k des filières recommandées avec un pourcentage de correspondance
        (la somme des pourcentages sur les 16 filières vaut 100%, pas seulement sur le top-k)."""
        w_content = self.w_content if w_content is None else w_content
        w_riasec = self.w_riasec if w_riasec is None else w_riasec

        sim_content_norm, sim_riasec, elig = self.score_components(serie, matiere, interets, caractere_letters)
        score = (w_content * sim_content_norm + w_riasec * sim_riasec) * elig
        proba = score / score.sum() if score.sum() > 0 else np.ones(len(self.filieres)) / len(self.filieres)

        ranking = sorted(zip(self.filieres, proba), key=lambda t: t[1], reverse=True)[:top_k]
        return [
            {
                "code": f["code"],
                "nom": f["nom"],
                "departement": f["departement"],
                # float() explicite : proba est un np.float64, non sérialisable en JSON tel quel
                "pourcentage": round(float(100 * p), 1),
            }
            for f, p in ranking
        ]
