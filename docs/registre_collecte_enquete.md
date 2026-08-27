# Registre de collecte — enquête ISPM (`src/orientia_ml/data/Sondage.csv`)

## Questionnaire effectivement diffusé

Les colonnes du fichier collecté correspondent exactement aux questions posées :

1. Horodateur (timestamp de réponse)
2. Genre
3. Êtes-vous ? (Étudiant / Professionnel)
4. Quelle était votre série en Terminale ?
5. Quelle a été votre matière préférée au Lycée ?
6. Si étudiant : quel parcours suivez-vous ? / Si professionnel : dans quel domaine exercez-vous ?
7. Quel(s) caractère(s) définissent votre personnalité ? *(auto-déclaratif, proche des libellés RIASEC)*
8. Quels sont vos centres d'intérêt ?
9. Êtes-vous satisfait de votre parcours académique ?
10. Votre travail actuel est-il en adéquation avec votre parcours académique ?
11. Où avez-vous fait vos études supérieures ?

## Populations et volumétrie

| | Valeur mesurée |
|---|---|
| **Réponses collectées (lignes du CSV)** | 155 |
| **Populations visées** | Étudiants ISPM (profil + parcours choisi) et professionnels déjà établis (profil + parcours suivi + adéquation métier réel), conformément aux deux populations recommandées par le sujet §5 |
| **Mode de diffusion** | Non tracé dans les données elles-mêmes — à documenter par l'équipe (formulaire en ligne, à en juger par la colonne Horodateur) |
| **Période de collecte** | Horodateurs observés le 26-27/08/2026 (voir `Horodateur` min/max du CSV) |
| **Réponses retenues pour l'évaluation du pipeline** | 149 (voir `src/orientia_ml/model/metrics.json` — évaluation du pipeline complet) ; l'écart avec les 155 lignes brutes correspond aux lignes incomplètes exclues avant évaluation |

## Anonymisation et consentement

- **Aucune donnée directement identifiante** (nom, email, téléphone) n'est présente dans les colonnes collectées — la structure du questionnaire ne demande que des informations de profil académique et de personnalité auto-déclarée.
- **Texte de consentement présenté aux répondants** : non conservé dans le dépôt actuel — **à fournir par l'équipe** si un formulaire de consentement explicite a été utilisé lors de la diffusion (obligation du sujet, §5, "Consentement et anonymisation").
- **Procédure d'anonymisation appliquée** : aucun traitement d'anonymisation supplémentaire n'a été nécessaire au vu de l'absence de champs nominatifs collectés à la source.

## Traitements postérieurs

- Nettoyage / exclusion des réponses incomplètes avant entraînement et évaluation (voir `orientia_model.ipynb` et `orientia_eval.ipynb`) — le détail exact des lignes exclues n'est pas conservé sous forme de rapport séparé dans ce dépôt.
- Recodage des réponses libres de personnalité vers les 6 lettres RIASEC pour l'entraînement du classifieur (`riasec_clf`).

## Biais d'échantillonnage constatés

- **Volume limité** (155 réponses) : intervalles de confiance larges, cohérent avec l'avertissement du sujet ("quelques centaines de réponses au mieux").
- **Auto-sélection** : les répondants sont probablement des proches du réseau de l'équipe/de l'ISPM — sur-représentation probable de certains parcours (à quantifier : voir répartition par parcours dans `orientia_eval.ipynb`).
- **Nature de l'étiquette** : chez les étudiants, le parcours renseigné est celui *choisi*, pas nécessairement celui qui *convenait* — biais reproduit par tout modèle entraîné dessus (voir `docs/note_limites_biais_risques.md`).
- **Classe rare** : la filière Tourisme est quasi absente des données externes RIASEC (voir `metrics.json`), donc quasiment jamais recommandée par le classifieur.

## Jeu de données externe complémentaire (`riasec.csv`)

- **Origine** : jeu public Kaggle de réponses à un test RIASEC (~146 000 lignes), utilisé uniquement pour entraîner le classifieur trait→département (`riasec_clf`), pas pour le score de similarité de contenu.
- **Statut** : externe, non spécifique à l'ISPM — sert à généraliser le lien personnalité→département au-delà des 155 réponses ISPM.

## À compléter par l'équipe avant remise finale

Les champs marqués « à fournir par l'équipe » ci-dessus (mode de diffusion précis, texte de
consentement, détail des exclusions) documentent une exigence explicite du sujet (§5, §4) que ce
registre ne peut pas reconstruire de façon fiable à partir des seules données du CSV — ils
dépendent du déroulement réel de la collecte, connu de l'équipe mais pas du dépôt de code.
