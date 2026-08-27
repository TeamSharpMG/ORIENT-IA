"""Exécute les 32 cas de eval/cases.py contre l'agent ORIENT'IA réel et produit :
- eval/results.json  : transcript brut + outils appelés + durée, par cas
- eval/rapport_evaluation.md : rapport lisible, groupé par catégorie

Usage : uv run python eval/run_eval.py
"""

from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cases import CASES  # noqa: E402

from orientia_rag.agent import build_agent  # noqa: E402
from orientia_rag.observability import tool_calls_since, turn_context  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
CATEGORIES = {
    "factuelle": "Questions factuelles sur les formations",
    "comparaison": "Comparaisons entre parcours",
    "ml_profil": "Profils nécessitant une recommandation ML",
    "multi_etapes": "Questions nécessitant plusieurs sources ou étapes",
    "info_absente": "Informations absentes du corpus",
    "ambigu": "Questions ambiguës ou profils incomplets",
    "securite": "Tests de sécurité et prompt injection",
    "biais": "Cas sensibles aux biais",
    "profilage": "Provenance des données et refus du profilage psychologique",
}


def run() -> list[dict]:
    print("Construction de l'agent...", flush=True)
    agent = build_agent()
    results = []

    for case in CASES:
        print(f"[{case['id']:2d}/{len(CASES)}] {case['categorie']} ...", flush=True)
        messages: list = []
        turns = []
        case_start = time.perf_counter()

        for user_msg in case["messages"]:
            messages.append({"role": "user", "content": user_msg})
            n_before = len(messages)
            with turn_context():
                t0 = time.perf_counter()
                try:
                    result = agent.invoke({"messages": messages})
                    duration_ms = round((time.perf_counter() - t0) * 1000, 1)
                    reply = result["messages"][-1].content
                    tools = tool_calls_since(result["messages"], n_before)
                    messages = result["messages"]
                    turns.append({
                        "question": user_msg,
                        "reponse": reply,
                        "outils_appeles": tools,
                        "duration_ms": duration_ms,
                        "erreur": None,
                    })
                except Exception as exc:  # noqa: BLE001
                    duration_ms = round((time.perf_counter() - t0) * 1000, 1)
                    turns.append({
                        "question": user_msg,
                        "reponse": None,
                        "outils_appeles": [],
                        "duration_ms": duration_ms,
                        "erreur": f"{type(exc).__name__}: {exc}",
                    })

        results.append({
            "id": case["id"],
            "categorie": case["categorie"],
            "duration_totale_ms": round((time.perf_counter() - case_start) * 1000, 1),
            "turns": turns,
        })

    return results


def write_report(results: list[dict]) -> None:
    OUT_DIR.mkdir(exist_ok=True)
    (OUT_DIR / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    by_cat: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_cat[r["categorie"]].append(r)

    all_durations = [t["duration_ms"] for r in results for t in r["turns"] if t["erreur"] is None]
    all_tools = [tool for r in results for t in r["turns"] for tool in t["outils_appeles"]]
    n_errors = sum(1 for r in results for t in r["turns"] if t["erreur"] is not None)

    lines = ["# Rapport d'évaluation ORIENT'IA", ""]
    lines.append(f"32 cas de test, {sum(len(r['turns']) for r in results)} tours au total.")
    lines.append("")
    lines.append("## Résumé mesuré")
    lines.append("")
    lines.append(f"- Tours en erreur : {n_errors} / {sum(len(r['turns']) for r in results)}")
    if all_durations:
        lines.append(f"- Latence par tour : min {min(all_durations):.0f} ms, "
                      f"moyenne {sum(all_durations)/len(all_durations):.0f} ms, max {max(all_durations):.0f} ms")
    tool_counts = defaultdict(int)
    for t in all_tools:
        tool_counts[t] += 1
    lines.append(f"- Appels d'outils : {dict(tool_counts)}")
    lines.append("")

    for cat_key, cat_label in CATEGORIES.items():
        cases = by_cat.get(cat_key, [])
        lines.append(f"## {cat_label} ({len(cases)} cas)")
        lines.append("")
        for r in cases:
            lines.append(f"### Cas {r['id']}")
            for t in r["turns"]:
                lines.append(f"- **Question :** {t['question']}")
                if t["erreur"]:
                    lines.append(f"  - **Erreur :** {t['erreur']}")
                else:
                    lines.append(f"  - **Outils appelés :** {t['outils_appeles'] or 'aucun'}")
                    lines.append(f"  - **Durée :** {t['duration_ms']:.0f} ms")
                    reponse = t["reponse"] or ""
                    apercu = reponse[:600] + ("…" if len(reponse) > 600 else "")
                    lines.append(f"  - **Réponse :** {apercu}")
            lines.append("")

    (OUT_DIR / "rapport_evaluation.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nRapport écrit dans {OUT_DIR / 'rapport_evaluation.md'}")
    print(f"Résultats bruts dans {OUT_DIR / 'results.json'}")


if __name__ == "__main__":
    write_report(run())
