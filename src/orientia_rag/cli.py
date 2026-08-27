"""Boucle de chat en ligne de commande pour ORIENT'IA."""

from .agent import build_agent
from .observability import llm_usage, log_event, timed, tool_calls_since, turn_context


def main() -> None:
    with timed("session.build_agent"):
        agent = build_agent()
    log_event("session.start")

    print("ORIENT'IA — assistant d'orientation universitaire (tapez 'exit' pour quitter)\n")
    messages = []
    try:
        while True:
            question = input("Vous : ").strip()
            if question.lower() in {"exit", "quit"}:
                break
            if not question:
                continue

            messages.append({"role": "user", "content": question})
            n_before = len(messages)
            with turn_context():
                with timed("chat.turn", question=question) as ctx:
                    result = agent.invoke({"messages": messages})
                    ctx["reponse_finale"] = result["messages"][-1].content
                    ctx["outils_appeles"] = tool_calls_since(result["messages"], n_before)
                    ctx.update(llm_usage(result["messages"][-1]))
            messages = result["messages"]
            print(f"\nORIENT'IA : {messages[-1].content}\n")
    finally:
        log_event("session.end")
