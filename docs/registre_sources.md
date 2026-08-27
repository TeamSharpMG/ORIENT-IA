# Registre des sources — corpus documentaire ORIENT'IA

Traçabilité des sources utilisées pour construire `src/orientia_rag/documents/ispm-edu.md`,
le corpus interrogé par le RAG (outil `search_ispm`).

| Champ | Valeur |
|---|---|
| **Titre** | Contenu institutionnel de l'ISPM (filières, admission, historique, vie pratique) |
| **Origine / URL** | https://ispm-edu.com/ |
| **Statut** | Officiel (site institutionnel de l'établissement) |
| **Date de consultation** | À confirmer par l'équipe (non horodatée automatiquement lors de la collecte initiale) |
| **Données extraites** | Liste des filières et départements, descriptions, mots-clés, séries de bac éligibles par filière, procédures et conditions d'admission, historique de l'établissement, informations pratiques (contact, vie étudiante) |
| **Traitement appliqué** | Contenu nettoyé et restructuré en Markdown, découpé par filière/section. Rubriques sans valeur d'orientation retirées (actualités, événements passés, annonces RH, galeries photo) — voir l'en-tête de `ispm-edu.md` |
| **Limites / incertitudes** | Un seul instantané du site à une date donnée : le contenu peut avoir changé depuis (frais, procédures). Aucune information chiffrée (frais exacts, taux d'insertion) au-delà de ce que le site publiait explicitement — voir la catégorie "informations absentes du corpus" du jeu d'évaluation (`eval/cases.py`, cas 20-22), qui vérifie que l'assistant reconnaît ces absences plutôt que de les inventer |

## Ce que le système fait de ces limites

- L'assistant ne répond **jamais** de mémoire sur l'ISPM : chaque réponse factuelle passe par `search_ispm`, dont chaque appel est loggé avec le texte de la requête, les passages récupérés et leur score BM25 (`logs/orientia.jsonl`, événement `rag.search`) — ce qui permet de vérifier a posteriori que la réponse est bien fondée sur ces sources.
- Si l'information demandée n'est pas dans le corpus, la règle de prompt (`agent.py`, "Règles de recherche") impose de le dire explicitement plutôt que d'inventer.

## À compléter par l'équipe

Ce registre documente ce qui est **structurellement vérifiable** dans le dépôt (origine du fichier,
traitement appliqué). La date exacte de consultation du site ISPM et le nom de la personne ayant
réalisé la collecte n'ont pas été conservés dans l'historique du projet — à renseigner par l'équipe
si le jury le demande.
