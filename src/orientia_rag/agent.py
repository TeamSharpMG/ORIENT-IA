"""Construction de l'agent ORIENT'IA : prompt système + outils (RAG + ML)."""

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool

from . import config
from .ml import recommend_filieres, verifier_eligibilite, warm_up
from .observability import timed
from .rag import build_retriever

_GROUNDING_RULES = """

## Règles de recherche (impératif)

- Pour toute question factuelle sur l'ISPM (filières, admission, historique, vie pratique, contact...), tu dois appeler l'outil `search_ispm` avant de répondre, même si tu penses déjà connaître la réponse. Ne réponds jamais de mémoire sur ces sujets.
- Base ta réponse uniquement sur le texte renvoyé par l'outil. N'ajoute aucun détail (chiffre, condition, nom, date) qui n'y figure pas explicitement.
- Si l'outil renvoie "Aucune information trouvée dans la base documentaire.", ou si le résultat ne répond pas à la question, dis-le clairement à l'utilisateur plutôt que d'inventer une réponse plausible.

## Règles de recommandation de filières (impératif)

- Dès que la conversation a réuni la série du bac, une matière préférée, les centres d'intérêt, et au moins un trait de personnalité RIASEC (Réaliste, Investigateur, Artistique, Social, Entreprenant, Conventionnel) de l'utilisateur, appelle l'outil `recommend_filieres` — ne calcule et n'invente jamais toi-même un classement de filières.
- S'il manque une de ces informations, demande-la avant d'appeler l'outil plutôt que de deviner une valeur.
- Présente exactement les 3 filières renvoyées par l'outil, dans l'ordre. Voir la section "Recommendation System" ci-dessus pour comment interpréter et présenter le résultat.
- En décrivant chaque filière, relie-la au caractère de l'utilisateur (ex: "avec ton côté Investigateur, cette filière est vraiment faite pour toi"), en te basant sur la vraie composante personnalité renvoyée par l'outil pour cette filière — jamais une connexion inventée.
- Termine toujours par un avis personnel, court et engageant, sur celle des 3 qui te semble la mieux adaptée et pourquoi — pas juste une liste neutre de pourcentages. Vois la section "Academic Guidance" ci-dessus pour le ton et les limites à respecter.
- Les traits RIASEC ne viennent JAMAIS d'une déduction de ta part (style d'écriture, ton, formulation) : demande-les toujours explicitement à l'utilisateur. Vois la section "Personality and Sensitive Criteria" ci-dessus — c'est une règle de sécurité, pas une préférence de style.

## Règles des autres outils (impératif)

- `comparer_parcours` : à appeler dès que l'utilisateur demande de comparer deux (ou plus) filières nommées ou par code. N'improvise jamais une comparaison à partir de ta mémoire — appelle l'outil puis synthétise son résultat.
- `verifier_eligibilite` : à appeler quand l'utilisateur demande si une série de bac précise donne accès à une filière précise (nommée ou par code). Rappelle systématiquement que ce score est une pondération de recommandation, pas une règle d'admission officielle — pour la vraie règle, utilise `search_ispm` en complément.
"""

SYSTEM_PROMPT = (config.DOCUMENTS_DIR / "contexts.md").read_text(encoding="utf-8") + _GROUNDING_RULES


def build_agent():
    llm = init_chat_model(
        model=config.LLM_MODEL,
        model_provider=config.LLM_PROVIDER,
        api_key=config.LLM_API_TOKEN,
    )

    retriever = build_retriever()
    warm_up()  # charge le pipeline ML au démarrage plutôt qu'au premier message.

    @tool
    def search_ispm(query: str) -> str:
        """Recherche dans la base documentaire de l'ISPM (filières, admission, historique, vie pratique, contact...).

        À appeler systématiquement avant de répondre à toute question factuelle sur l'ISPM,
        même si la réponse semble évidente : ne jamais répondre de mémoire sur ces sujets.
        """
        with timed("rag.search", query=query) as ctx:
            hits = retriever.search_with_scores(query, k=config.RETRIEVER_K)
            ctx["n_resultats"] = len(hits)
            ctx["passages"] = [{"score": round(s, 3), "extrait": c[:80]} for c, s in hits]
        if not hits:
            return "Aucune information trouvée dans la base documentaire."
        return "\n\n---\n\n".join(chunk for chunk, _score in hits)

    @tool("recommend_filieres")
    def recommend_filieres_tool(
        serie_bac: str,
        matiere_preferee: str,
        interets: str,
        traits_personnalite: list[str],
    ) -> str:
        """Calcule, via le modèle ML entraîné (jamais à deviner soi-même), le top 3 des
        filières ISPM les plus adaptées à un profil élève.

        À appeler dès que la conversation a réuni : la série du bac (ex: "D"), une matière
        préférée, les centres d'intérêt (texte libre), et au moins un trait de personnalité
        parmi Réaliste, Investigateur, Artistique, Social, Entreprenant, Conventionnel (RIASEC).

        Retourne pour chacune des 3 filières : le nom, le département, un pourcentage de
        correspondance, et la décomposition du score (similarité intérêts / correspondance
        personnalité / éligibilité de la série) à utiliser pour expliquer le choix.
        """
        resultats = recommend_filieres(
            serie=serie_bac,
            matiere=matiere_preferee,
            interets=interets,
            caractere_letters=traits_personnalite,
        )
        if not resultats:
            return "Aucune recommandation calculable avec ces informations."

        lignes = []
        for rang, r in enumerate(resultats, start=1):
            exp = r["explication"]
            lignes.append(
                f"{rang}. {r['nom']} ({r['code']}) — {r['departement']} — {r['pourcentage']}% de correspondance\n"
                f"   - Similarité avec les intérêts/matière : {exp['similarite_interets']}\n"
                f"   - Correspondance personnalité (RIASEC) : {exp['correspondance_personnalite']}\n"
                f"   - Éligibilité de la série {serie_bac} : {exp['eligibilite_serie']}"
            )
        return "\n\n".join(lignes)

    @tool("comparer_parcours")
    def comparer_parcours_tool(filiere_a: str, filiere_b: str) -> str:
        """Récupère les informations documentaires de deux filières ISPM pour les comparer
        (ex: "Compare ISAIA et IGGLIA"). Fait une recherche documentaire distincte pour
        chacune et renvoie les deux résultats côte à côte — c'est à toi de synthétiser
        la comparaison ensuite, en citant uniquement ce que ces résultats contiennent.
        """
        with timed("rag.compare", filiere_a=filiere_a, filiere_b=filiere_b) as ctx:
            hits_a = retriever.search_with_scores(filiere_a, k=config.RETRIEVER_K)
            hits_b = retriever.search_with_scores(filiere_b, k=config.RETRIEVER_K)
            ctx["passages_a"] = [{"score": round(s, 3), "extrait": c[:80]} for c, s in hits_a]
            ctx["passages_b"] = [{"score": round(s, 3), "extrait": c[:80]} for c, s in hits_b]

        bloc_a = "\n\n".join(c for c, _s in hits_a) if hits_a else "Aucune information trouvée."
        bloc_b = "\n\n".join(c for c, _s in hits_b) if hits_b else "Aucune information trouvée."
        return (
            f"=== {filiere_a} ===\n{bloc_a}\n\n"
            f"=== {filiere_b} ===\n{bloc_b}"
        )

    @tool("verifier_eligibilite")
    def verifier_eligibilite_tool(serie_bac: str, code_filiere: str) -> str:
        """Calcule (via le modèle ML, jamais à deviner soi-même) un score d'éligibilité
        heuristique entre une série de bac et UNE filière ISPM précise désignée par son
        code (ex: "ISAIA"). N'est PAS une règle d'admission officielle — seulement une
        pondération de recommandation ; rappelle-le systématiquement à l'utilisateur.
        """
        resultat = verifier_eligibilite(serie_bac, code_filiere)
        if resultat is None:
            return f"Code filière \"{code_filiere}\" inconnu."
        return (
            f"{resultat['nom']} ({resultat['code']}) — {resultat['departement']} : "
            f"score d'éligibilité heuristique {resultat['score_eligibilite']} pour la série {serie_bac} "
            f"(1.0 = série listée, 0.6 = partiellement incertain, 0.4 = incertain/non listé — "
            f"pas une règle d'admission officielle)."
        )

    return create_agent(
        model=llm,
        tools=[search_ispm, recommend_filieres_tool, comparer_parcours_tool, verifier_eligibilite_tool],
        system_prompt=SYSTEM_PROMPT,
    )
