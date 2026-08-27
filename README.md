# ORIENT'IA

Assistant intelligent d'orientation pédagogique pour l'ISPM (Institut Supérieur Polytechnique de
Madagascar) — combine recherche documentaire (RAG), un modèle de Machine Learning entraîné sur des
données réelles, et un agent conversationnel (LLM + outils) capable d'expliquer et de tracer chacune
de ses recommandations.

> ORIENT'IA constitue un outil d'aide à l'orientation. Ses recommandations ne remplacent ni l'avis
> d'un conseiller pédagogique ni une décision officielle d'admission.

## Structure du dépôt

```
src/
├── orientia_ml/     # pipeline ML entraîné (RandomForest RIASEC + similarité d'embeddings)
│   ├── data/            Sondage.csv (155 réponses ISPM), riasec.csv (dataset externe Kaggle)
│   ├── model/            orientia_pipeline.joblib, metrics.json, courbes
│   ├── orientia_model.ipynb   notebook d'entraînement
│   ├── orientia_eval.ipynb    notebook de mesure des métriques
│   └── orientia_pipeline.py   module d'inférence, importé tel quel par orientia_rag
├── orientia_rag/     # agent LangChain, outils, RAG, API FastAPI, logging
│   ├── documents/         contexts.md (prompt système), ispm-edu.md (corpus RAG)
│   ├── agent.py            construction de l'agent + définition des 4 outils
│   ├── rag.py               chunking + recherche BM25
│   ├── ml.py                 intégration du pipeline ML dans l'agent
│   ├── api.py                 API HTTP (FastAPI)
│   ├── cli.py                  chat en ligne de commande
│   └── observability.py         logs structurés JSONL + mesure de durées
└── orientia_app/     # point d'entrée web : page de test (index.html) + logo
eval/                # jeu de 32 cas de test + script d'exécution + résultats mesurés
docs/                # registre des sources, registre de collecte, note de limites, schéma d'architecture
```

## Installation

Prérequis : [uv](https://docs.astral.sh/uv/), Python ≥ 3.14.

```bash
uv sync
```

Créer un fichier `.env` à la racine avec les identifiants du LLM (compatible OpenRouter ou tout
provider géré par `langchain.chat_models.init_chat_model`) :

```env
LLM_PROVIDER=openrouter
LLM_MODEL=<nom-du-modèle>
LLM_API_TOKEN=<votre-clé-api>
```

Au premier lancement, le modèle d'embeddings (`paraphrase-multilingual-MiniLM-L12-v2`, ~470 Mo) se
télécharge automatiquement depuis HuggingFace et se met en cache localement.

## Exécution

**Application web (API + interface de chat) :**

```bash
uv run orientia-app
```

Ouvrir `http://127.0.0.1:8000/` (interface de test : profil → recommandation ML → chat libre) ou
`http://127.0.0.1:8000/docs` (Swagger). Rechargement automatique en développement :

```bash
uv run uvicorn orientia_rag.api:app --reload
```

**Chat en ligne de commande :**

```bash
uv run orientia-rag
```

## Évaluation

Le jeu de 32 cas de test (couvrant les 9 catégories imposées par le protocole d'évaluation) se
relance avec :

```bash
uv run python eval/run_eval.py
```

Produit `eval/results.json` (transcript brut) et `eval/rapport_evaluation.md` (rapport lisible,
groupé par catégorie, avec outils appelés et latence par tour).

## Observabilité

Chaque tour de conversation, appel d'outil (RAG et ML) et requête HTTP est loggé en JSON structuré
dans `logs/orientia.jsonl` (une ligne par événement, corrélée par `turn_id`) :

```bash
tail -f logs/orientia.jsonl | python3 -m json.tool
```

Voir `src/orientia_rag/observability.py`.

## Documentation complémentaire

- [`docs/schema_architecture.md`](docs/schema_architecture.md) — schéma d'architecture (diagramme Mermaid)
- [`docs/registre_sources.md`](docs/registre_sources.md) — traçabilité du corpus documentaire
- [`docs/registre_collecte_enquete.md`](docs/registre_collecte_enquete.md) — traçabilité du sondage ISPM
- [`docs/note_limites_biais_risques.md`](docs/note_limites_biais_risques.md) — limites, biais et risques
- [`src/orientia_ml/README.md`](src/orientia_ml/README.md) — détail du pipeline ML et de ses métriques
- [`docs/grille_evaluation.md`](docs/grille_evaluation.md) — correspondance entre la grille d'évaluation et le dépôt
