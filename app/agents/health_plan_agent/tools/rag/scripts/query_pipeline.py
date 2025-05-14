#!/usr/bin/env python3
"""
scripts/query_pipeline.py

Script CLI para testar o pipeline RAG: lê uma pergunta do usuário via argumento,
instancia o pipeline RAG e imprime a resposta gerada pelo LLM.
"""

import argparse
from dotenv import load_dotenv

from app.agents.health_plan_agent.tools.rag.pipeline.rag_pipeline import RAGPipeline


def main() -> None:
    """
    Ponto de entrada para executar consultas via pipeline RAG.
    """
    # Carrega variáveis de ambiente definidas em .env
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Executa uma consulta usando o pipeline RAG"
    )
    parser.add_argument(
        "-q", "--query",
        type=str,
        required=True,
        help="Pergunta para o pipeline RAG"
    )
    parser.add_argument(
        "-k", "--top_k",
        type=int,
        default=None,
        help="Número de trechos a recuperar (substitui o padrão do pipeline)"
    )
    args = parser.parse_args()

    # Determina quantos contextos recuperar
    if args.top_k is not None:
        pipeline = RAGPipeline(k=args.top_k)
    else:
        pipeline = RAGPipeline()

    # Executa o pipeline e imprime a resposta
    answer = pipeline.run(args.query)
    print(answer)


if __name__ == "__main__":
    main()
