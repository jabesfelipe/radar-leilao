# Radar Leilão

MVP em português do Brasil para análise rastreável de imóveis em leilões extrajudiciais.

## Executar localmente

Pré-requisitos: Docker Desktop com integração WSL habilitada, Python 3.12+ e Node.js 20+.

```powershell
docker compose up -d
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
uvicorn app.main:app --app-dir backend --reload --port 8000
```

Em outro terminal:

```powershell
npm install --prefix frontend
npm run dev --prefix frontend
```

Frontend: http://localhost:5173  
API/documentação: http://localhost:8000/docs

A chave de LLM é opcional no MVP inicial. O gateway fica desacoplado para configuração posterior via `LLM_API_KEY`.
