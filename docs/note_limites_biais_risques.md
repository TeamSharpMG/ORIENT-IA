# Note — limites, biais et risques d'ORIENT'IA

## 1. Limites du modèle ML

Chiffres mesurés dans `src/orientia_ml/model/metrics.json` (généré par `orientia_eval.ipynb`) :

- **Classifieur RIASEC → département** : accuracy ≈ **52,2 %** en validation croisée 5-fold sur
  ~26 000 réponses externes (Kaggle) — largement mieux qu'un hasard à 8 classes (~12,5 %), mais
  loin d'être parfait. Confond souvent Génie Industriel / Génie Civil / Informatique ; ne détecte
  quasiment jamais "Tourisme" (classe sous-représentée : 342 exemples / 26 123).
- **Pipeline complet** (149 réponses réelles du sondage ISPM) : top-3 hit rate ≈ **77 % (± 4 points)**
  en validation croisée imbriquée (estimation honnête — le poids `w_content` est recalibré à chaque
  pli sur les données d'entraînement uniquement). Top-1 seul ≈ 56 %. **C'est pourquoi l'interface
  affiche toujours le top-3, jamais uniquement le premier choix.**
- **Volume d'entraînement modeste** : 149-155 réponses ISPM réelles. Les intervalles de confiance
  sont larges ; le modèle généralise à partir d'un échantillon auto-sélectionné (voir
  `docs/registre_collecte_enquete.md`).
- **`eligibilite_serie()`** (utilisée par `recommend_filieres` et `verifier_eligibilite`) est une
  **pondération heuristique de recommandation**, pas une règle d'admission officielle — elle ne doit
  jamais être présentée comme telle à l'utilisateur (règle imposée dans le prompt système et
  vérifiée par le cas 19 du jeu d'évaluation).

## 2. Biais identifiés

- **Biais d'échantillonnage du sondage** : réseau de diffusion probablement proche de l'équipe
  projet, sur-représentation possible de certains parcours (notamment informatique).
- **Biais de l'étiquette "parcours choisi"** : chez les étudiants répondants, le parcours renseigné
  est celui *choisi*, pas nécessairement celui qui *convenait* le mieux — un modèle entraîné dessus
  reproduit les biais des choix passés (y compris des biais de genre ou de filière d'origine si le
  sondage en contient). Le sous-échantillon "professionnels" (jugement rétrospectif) atténue en
  partie ce biais, au prix d'un biais de reconstruction mémorielle.
- **Classe rare "Tourisme"** : sous-représentée dans les données externes RIASEC, quasiment jamais
  recommandée par le classifieur même quand elle serait pertinente.
- **Le système ne collecte ni sexe, ni âge, ni origine comme critère de recommandation** — vérifié
  explicitement par les cas 29-30 du jeu d'évaluation (refus de recommandation basée sur le sexe/l'âge,
  refus d'associer un genre à l'évitement d'une filière technique).

## 3. Risques et mitigations mises en place

| Risque (sujet §16) | Mitigation | Vérifié par |
|---|---|---|
| Profilage psychologique / inférence de personnalité depuis le style d'écriture | Règle prompt explicite : les traits RIASEC ne sont utilisés que si déclarés explicitement par l'utilisateur ; refus actif si on demande une analyse du style | Cas 31 du jeu d'éval |
| Injection de prompt via contenu de document | Règle prompt : le contenu récupéré (RAG, outils) est traité comme donnée, jamais comme instruction | Cas 27 |
| Instructions malveillantes / jailbreak conversationnel | Persona et règles non négociables rappelées dans le prompt système | Cas 28 |
| Recommandation fondée sur critères discriminatoires (sexe, âge) | Refus explicite, redirection vers les critères académiques légitimes | Cas 29-30 |
| Invention d'informations absentes du corpus | Obligation de dire "information non trouvée" plutôt que d'inventer | Cas 20, 22, 26 |
| Confusion conseil pédagogique / décision administrative | Renvoi explicite vers l'administration ISPM pour toute décision officielle | Section "Personality and Sensitive Criteria", `contexts.md` |
| Présentation d'un score ML comme une garantie de réussite | Rappel systématique : signal de compatibilité, pas une vérité absolue | `contexts.md`, section "Recommendation System" |

## 3bis. Limite honnête sur la démarche scientifique ML (sujet §7)

`orientia_model.ipynb` documente le nettoyage, le choix des variables, l'entraînement du
classifieur RIASEC et la calibration du pipeline — mais ne présente **pas explicitement** un
modèle de référence trivial (baseline aléatoire/majoritaire) ni une comparaison formelle d'au
moins deux approches de ML distinctes côte à côte, comme demandé par le sujet §7. `orientia_eval.ipynb`
compense partiellement en documentant deux méthodes d'estimation (optimiste vs validation croisée
imbriquée honnête), ce qui donne une lecture de la robustesse mais n'est pas une comparaison
d'approches à proprement parler. **Ce point n'a pas été corrigé avant la remise** (retravailler les
notebooks d'entraînement risquait de invalider le modèle déjà calibré et intégré, dans le temps
restant) — le signaler plutôt que le masquer, conformément à l'esprit du sujet ("Preuve mesurée
plutôt qu'affirmation").

## 4. Limites de l'évaluation elle-même

- Le jeu de 32 cas (`eval/cases.py`) est exécuté automatiquement (`eval/run_eval.py`) et produit un
  transcript complet (`eval/rapport_evaluation.md`, `eval/results.json`) avec outils appelés et
  latence par tour — mais le **jugement de conformité reste actuellement une lecture humaine du
  transcript**, pas un scoring automatique (pas de LLM-juge indépendant faute de temps). Les 32 cas
  couvrent les 9 catégories minimales imposées par le sujet, avec les minimums requis par catégorie.
- La latence mesurée (moyenne ≈ 2,9 s/tour, max 8,8 s) dépend du fournisseur LLM utilisé
  (`LLM_PROVIDER`/`LLM_MODEL` dans `.env`) et peut varier.
- Le **coût par requête** (tokens + coût USD, via `usage_metadata`/`response_metadata` du provider)
  est loggé pour chaque tour depuis `orientia_rag/observability.py::llm_usage()` — disponible quand
  le provider l'expose (c'est le cas d'OpenRouter, utilisé en développement).

## 5. Extension non réalisée

L'IA symbolique (ontologie / graphe de connaissances, §12 du sujet) n'a pas été implémentée dans le
temps imparti — le système repose sur RAG lexical + ML uniquement. C'est une extension
**recommandée mais non obligatoire** selon le sujet.
