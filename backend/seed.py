"""Carga inicial da base — cria parâmetros, usuários e dados de demonstração.

    python backend/seed.py                  # admin + parâmetros + demonstração
    python backend/seed.py --sem-demo       # só o essencial (produção)
    python backend/seed.py --dias 365       # histórico maior para o dashboard
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(message)s")


def main() -> int:
    analisador = argparse.ArgumentParser(description="Carga inicial do ParouAí")
    analisador.add_argument("--sem-demo", action="store_true", help="não cria dados fictícios")
    analisador.add_argument("--dias", type=int, default=120, help="dias de histórico sintético")
    argumentos = analisador.parse_args()

    from app.services import seed

    try:
        resumo = seed.executar(com_demo=not argumentos.sem_demo, dias_historico=argumentos.dias)
    except Exception as erro:
        print(f"\n❌ Falha na carga: {erro}\n", file=sys.stderr)
        print(
            "Verifique as credenciais do Firebase no arquivo .env "
            "(FIREBASE_CREDENTIALS_FILE) ou use FIRESTORE_EMULATOR_HOST.",
            file=sys.stderr,
        )
        return 1

    print("\n✅ Carga concluída:")
    for chave, valor in resumo.items():
        print(f"   {chave}: {valor}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
