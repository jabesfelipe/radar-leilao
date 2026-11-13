"""Runner do worker de processamento de documentos (Fase 6).

Loop simples de polling sobre a fila DB-backed (ver documents/worker.py). Projetado
para rodar como container separado em produção (serviço `worker` do compose). Sem
Redis/Celery: o estado durável é a própria tabela ``document_versions``.

Execução:
    python -m app.worker_main            # loop contínuo (intervalo WORKER_INTERVAL_SECONDS)
    python -m app.worker_main --once     # uma varredura e sai (útil em cron/CI)

Variáveis:
    WORKER_INTERVAL_SECONDS (default 30), WORKER_BATCH_LIMIT (default 10),
    WORKER_MAX_ATTEMPTS (default 5), WORKER_LEASE_SECONDS (default 600; prazo após o qual
    uma tentativa sem conclusão é tratada como interrompida/crash).
Encerramento gracioso: SIGTERM/SIGINT interrompem o loop entre varreduras.
"""
from __future__ import annotations

import os
import signal
import sys
import time

from .database import SessionLocal
from .logging_config import configure_logging, get_logger
from .documents.worker import LEASE_SECONDS_DEFAULT, run_once

configure_logging()
log = get_logger("worker")

_stop = False


def _handle_stop(signum, _frame):
    global _stop
    _stop = True
    log.info("worker: sinal %s recebido; encerrando após a varredura atual.", signum)


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    once = "--once" in argv
    interval = int(os.getenv("WORKER_INTERVAL_SECONDS", "30"))
    batch = int(os.getenv("WORKER_BATCH_LIMIT", "10"))
    max_attempts = int(os.getenv("WORKER_MAX_ATTEMPTS", "5"))
    lease_seconds = int(os.getenv("WORKER_LEASE_SECONDS", str(LEASE_SECONDS_DEFAULT)))

    signal.signal(signal.SIGTERM, _handle_stop)
    signal.signal(signal.SIGINT, _handle_stop)

    log.info("worker iniciado (once=%s interval=%ss batch=%s max_attempts=%s)", once, interval, batch, max_attempts)
    while not _stop:
        try:
            db = SessionLocal()
            try:
                result = run_once(db, limit=batch, max_attempts=max_attempts, lease_seconds=lease_seconds)
                if result["interrompidas"]:
                    log.warning("worker: %s tentativa(s) interrompida(s) recuperada(s).", len(result["interrompidas"]))
                if result["processadas"]:
                    log.info("worker: varredura processou %s versao(oes).", result["processadas"])
            finally:
                db.close()
        except Exception as exc:  # o worker nunca morre por erro de uma varredura
            log.warning("worker: erro na varredura (%s); continuando.", type(exc).__name__)
        if once:
            break
        # Sono fatiado para responder rápido ao sinal de parada.
        slept = 0
        while slept < interval and not _stop:
            time.sleep(1)
            slept += 1
    log.info("worker encerrado.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
