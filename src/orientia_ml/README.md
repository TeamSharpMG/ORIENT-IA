# ORIENT'IA — package d'intégration

Ce dossier est **autosuffisant** : il contient tout ce qu'il faut pour (a) intégrer le modèle
dans une app, et (b) reproduire/mesurer ses métriques, sans dépendre du reste du repo.

```
orientia_export/
├── README.md                  <- ce fichier
├── orientia_pipeline.py       <- module Python à importer tel quel dans l'app
├── orientia_eval.ipynb        <- notebook de métriques (n'entraîne rien, mesure seulement)
├── model/
│   ├── orientia_pipeline.joblib   <- pipeline entraîné + calibré (59 Mo, compressé)
│   ├── metrics.json                <- dernières métriques mesurées (généré par orientia_eval.ipynb)
│   ├── confusion_matrix.png        <- généré par orientia_eval.ipynb
│   └── metrics_summary.png         <- généré par orientia_eval.ipynb
└── data/
    ├── Sondage.csv             <- 155 réponses au sondage ISPM (utilisé par orientia_eval.ipynb)
    └── riasec.csv              <- ~146k réponses RIASEC externes (Kaggle, utilisé par orientia_eval.ipynb)
```

Le notebook d'entraînement original (`orientia_model.ipynb`, qui construit et calibre le
pipeline à partir de zéro) reste à la racine du repo — ce dossier n'en est que le livrable final.
`data/` n'est nécessaire **que** pour ré-exécuter `orientia_eval.ipynb` (mesurer les métriques) ;
**l'app en production n'a besoin que de `orientia_pipeline.py` + `model/orientia_pipeline.joblib`**.

## Intégration dans une app

### Dépendances

```
pip install sentence-transformers scikit-learn numpy joblib
```

Testé avec `scikit-learn==1.9.0`, `sentence-transformers==6.0.0`, `numpy==2.5.2` — un décalage de
version scikit-learn peut faire échouer le `joblib.load()` du RandomForest (message d'erreur
explicite dans ce cas ; réentraîner avec `orientia_model.ipynb` si besoin).

Le modèle d'embeddings (`paraphrase-multilingual-MiniLM-L12-v2`, ~470 Mo) se télécharge
automatiquement depuis HuggingFace au premier appel et se met en cache localement
(`~/.cache/huggingface`) — prévoir cet accès réseau au premier démarrage du service (ou
pré-télécharger l'image Docker avec le cache déjà rempli).

### Code

```python
from orientia_pipeline import OrientiaPipeline

# Chargement une seule fois au démarrage de l'app (coûte ~1-2s pour le joblib,
# quelques secondes pour le modèle d'embeddings si déjà en cache local)
pipeline = OrientiaPipeline.load("model/orientia_pipeline.joblib")

resultats = pipeline.predict(
    serie="D",                                            # série du bac (C, D, S, A, TGI, L, ...)
    matiere="Mathématiques",                              # matière préférée au lycée (texte libre)
    interets="jeux vidéo, robotique, programmation",      # centres d'intérêt (texte libre)
    caractere_letters={"I", "R"},                         # sous-ensemble de {R,I,A,S,E,C}
    top_k=5,
)
```

`resultats` est une liste de dicts directement sérialisable en JSON :

```json
[
  {"code": "ISAIA", "nom": "Informatique, Statistique Appliquée et Intelligence Artificielle",
   "departement": "Informatique et Télécommunications", "pourcentage": 14.0},
  ...
]
```

Les pourcentages somment à 100% sur les **16 filières**, pas seulement sur le `top_k` retourné.

### Ce que l'app doit collecter côté utilisateur

| Paramètre | Format attendu | Exemple |
|---|---|---|
| `serie` | texte libre, une des séries connues idéalement (`C`, `D`, `S`, `A`/`A2`, `TGI`, ou "Techniques agricoles"/"Techniques du génie civil" en toutes lettres) | `"D"` |
| `matiere` | texte libre | `"Mathématiques"` |
| `interets` | texte libre, phrase ou liste de mots-clés | `"jeux vidéo, robotique"` |
| `caractere_letters` | `set`/liste de lettres parmi `R I A S E C` (test RIASEC — Réaliste, Investigateur, Artistique, Social, Entreprenant, Conventionnel) | `{"I", "R"}` |

Une série de bac inconnue ou une lettre RIASEC en dehors de `RIASEC` ne fait pas planter le
pipeline : elle reçoit simplement un score d'éligibilité par défaut (0.4, "incertain") — voir
`eligibilite_serie()` dans `orientia_pipeline.py`.

### API attendue de `OrientiaPipeline`

- `OrientiaPipeline.load(joblib_path, embed_model=None)` — charge le pipeline. Passer
  `embed_model` permet de réutiliser une instance `SentenceTransformer` déjà chargée ailleurs
  dans l'app (évite de la charger deux fois si l'app fait aussi d'autres tâches NLP).
- `pipeline.predict(serie, matiere, interets, caractere_letters, top_k=5, w_content=None, w_riasec=None)`
  — retourne le top-k. `w_content`/`w_riasec` sont optionnels : par défaut ceux calibrés dans le
  joblib (`w_content=0.4`, `w_riasec=0.6`), à ne changer que si vous recalibrez sur davantage de
  données (voir `orientia_model.ipynb`, section 6).
- `pipeline.score_components(...)` — expose séparément les 3 composantes du score (contenu,
  RIASEC, éligibilité) avant combinaison ; utile pour du debug ou de l'explicabilité côté UI
  ("pourquoi cette filière ?").

## Qualité du modèle (voir `orientia_eval.ipynb` et `model/metrics.json` pour le détail)

- **Classifieur RIASEC → département** : accuracy ≈ 52% en validation croisée 5-fold sur ~26 000
  réponses externes (Kaggle). Fiable sur "Techniques des Affaires" et "Biotechnologie et
  Agronomie" ; confond souvent Génie Industriel / Génie Civil / Informatique ; ne détecte quasiment
  jamais "Tourisme" (classe trop rare, 342 exemples).
- **Pipeline complet** (sur les 149 réponses réelles du sondage ISPM) :
  - top-3 hit rate ≈ **80.5%** évalué sur les mêmes données ayant servi à choisir le poids
    `w_content` (chiffre "tel qu'il est livré aujourd'hui" — c'est celui du notebook d'entraînement).
  - top-3 hit rate ≈ **77% (± ~4 points)** en validation croisée imbriquée (poids recalibré à
    chaque pli sur les données d'entraînement uniquement) — estimation plus honnête de la
    généralisation attendue en production.
  - top-1 ≈ 56%, top-5 ≈ 87% (au poids livré).

**À retenir pour l'app** : afficher le top-3 ou top-5, pas seulement le top-1 — le taux de succès
chute nettement en ne gardant que la meilleure filière. `eligibilite_serie()` est une **heuristique
de pondération de recommandation**, pas une règle d'admission — ne pas l'utiliser pour dire à un
utilisateur qu'il est/n'est pas éligible à l'ISPM (voir `ispm-edu.md` à la racine du repo pour les
vraies règles d'admission par série).

## Recalibrer / réentraîner

Toute la logique d'entraînement (nettoyage, entraînement du RandomForest, calibration du poids
`w_content`) vit dans `orientia_model.ipynb` à la racine du repo — pas dans ce dossier. Pour mettre
à jour le modèle exporté ici après une réexécution de ce notebook :

```python
import joblib
d = joblib.load("orientia_pipeline.joblib")          # sortie de orientia_model.ipynb
joblib.dump(d, "orientia_export/model/orientia_pipeline.joblib", compress=3)
```

Puis relancer `orientia_eval.ipynb` pour mettre à jour `model/metrics.json`.
