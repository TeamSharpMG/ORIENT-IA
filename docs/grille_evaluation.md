# Correspondance grille d'évaluation ↔ dépôt

Ce document fait le lien entre chaque critère de la grille d'évaluation et son emplacement
concret dans le dépôt. Barème total : 100 points.

## Vue d'ensemble

| # | Critère | Points | Emplacement principal |
|---|---|:-:|---|
| 1 | Acquisition, qualité et traçabilité des données | 12 | `docs/registre_collecte_enquete.md`, `docs/registre_sources.md` |
| 2 | Analyse des données et démarche scientifique | 10 | `src/orientia_ml/orientia_model.ipynb` |
| 3 | Machine Learning et analyse des résultats | 18 | `src/orientia_ml/orientia_model.ipynb`, `orientia_eval.ipynb`, `model/metrics.json` |
| 4 | Intégration du modèle au système | 10 | `src/orientia_rag/ml.py`, `src/orientia_rag/config.py` |
| 5 | RAG, recherche et gestion des sources | 12 | `src/orientia_rag/rag.py`, `documents/ispm-edu.md` |
| 6 | Agent conversationnel et outils | 12 | `src/orientia_rag/agent.py`, `cli.py`, `api.py` |
| 7 | Évaluation expérimentale de bout en bout | 14 | `eval/cases.py`, `eval/run_eval.py`, `eval/rapport_evaluation.md` |
| 8 | Observabilité, sécurité et gestion des biais | 7 | `src/orientia_rag/observability.py`, `docs/note_limites_biais_risques.md` |
| 9 | Démonstration, vidéo et qualité du dépôt | 5 | `README.md`, `docs/schema_architecture.md` — ⚠️ vidéo manquante |
| | **Total** | **100** | |

## Détail par critère

### 1. Acquisition, qualité et traçabilité des données — 12 pts

- [`docs/registre_collecte_enquete.md`](registre_collecte_enquete.md) — registre de collecte du sondage ISPM (155 réponses)
- [`docs/registre_sources.md`](registre_sources.md) — traçabilité des sources du corpus documentaire RAG
- [`src/orientia_ml/data/`](../src/orientia_ml/data/) — données brutes : `Sondage.csv`, `riasec.csv`

### 2. Analyse des données et démarche scientifique — 10 pts

- [`src/orientia_ml/orientia_model.ipynb`](../src/orientia_ml/orientia_model.ipynb) — nettoyage, choix des variables, entraînement
- [`docs/note_limites_biais_risques.md`](note_limites_biais_risques.md) (§3bis) — limite honnête sur la démarche scientifique

### 3. Machine Learning et analyse des résultats — 18 pts

- [`src/orientia_ml/orientia_model.ipynb`](../src/orientia_ml/orientia_model.ipynb) — entraînement du RandomForest RIASEC + calibration
- [`src/orientia_ml/orientia_eval.ipynb`](../src/orientia_ml/orientia_eval.ipynb) — mesure des métriques, produit :
  - `model/metrics.json`
  - `model/confusion_matrix.png`
  - `model/metrics_summary.png`
- [`src/orientia_ml/orientia_pipeline.py`](../src/orientia_ml/orientia_pipeline.py) — module d'inférence livré (`OrientiaPipeline`)

### 4. Intégration du modèle au système — 10 pts

- [`src/orientia_rag/ml.py`](../src/orientia_rag/ml.py) — enveloppe `OrientiaPipeline` dans l'agent
- [`src/orientia_rag/config.py`](../src/orientia_rag/config.py) — chemin du `.joblib`
- [`src/orientia_rag/api.py`](../src/orientia_rag/api.py) — chargement unique au démarrage via `lifespan()`
- [`src/orientia_ml/README.md`](../src/orientia_ml/README.md) — doc d'intégration du pipeline

### 5. RAG, recherche et gestion des sources — 12 pts

- [`src/orientia_rag/rag.py`](../src/orientia_rag/rag.py) — chunking Markdown + index BM25
- [`src/orientia_rag/documents/ispm-edu.md`](../src/orientia_rag/documents/ispm-edu.md) — corpus documentaire
- [`src/orientia_rag/documents/contexts.md`](../src/orientia_rag/documents/contexts.md) — prompt système
- [`docs/registre_sources.md`](registre_sources.md) — traçabilité des sources

### 6. Agent conversationnel et outils — 12 pts

- [`src/orientia_rag/agent.py`](../src/orientia_rag/agent.py) — construction de l'agent + 4 outils :
  `search_ispm`, `recommend_filieres`, `comparer_parcours`, `verifier_eligibilite`
- [`src/orientia_rag/cli.py`](../src/orientia_rag/cli.py) — interface terminal
- [`src/orientia_app/index.html`](../src/orientia_app/index.html) — interface web (via `api.py`)

### 7. Évaluation expérimentale de bout en bout — 14 pts

- [`eval/cases.py`](../eval/cases.py) — 32 cas de test, 9 catégories (factuelle, comparaison, ml_profil,
  multi_etapes, info_absente, ambigu, securite, biais, profilage)
- [`eval/run_eval.py`](../eval/run_eval.py) — script d'exécution
- [`eval/results.json`](../eval/results.json) — transcript brut
- [`eval/rapport_evaluation.md`](../eval/rapport_evaluation.md) — rapport lisible groupé par catégorie

### 8. Observabilité, sécurité et gestion des biais — 7 pts

- [`src/orientia_rag/observability.py`](../src/orientia_rag/observability.py) — logs JSONL structurés
  (`logs/orientia.jsonl` : turn_id, durées, outils appelés, sources RAG)
- [`docs/note_limites_biais_risques.md`](note_limites_biais_risques.md) — biais identifiés, risques, mitigations
- Catégories `securite` / `biais` / `profilage` dans [`eval/cases.py`](../eval/cases.py)

### 9. Démonstration, vidéo et qualité du dépôt — 5 pts

- [`README.md`](../README.md) — présentation, installation, exécution
- [`docs/schema_architecture.md`](schema_architecture.md) — schéma d'architecture (diagramme Mermaid)
- **⚠️ Manquant** : aucune vidéo de démonstration trouvée dans le dépôt (ni fichier `.mp4`/`.mov`,
  ni lien vers une vidéo hébergée). À ajouter si ce critère l'exige.
