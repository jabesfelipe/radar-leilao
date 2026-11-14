from pathlib import Path
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Radar Leilão API"
    database_url: str = "postgresql+psycopg://radar:radar_local@localhost:5432/radar_leilao"
    storage_dir: str = "storage/documents"
    # Abstração de storage (Fase 4): "local" (padrão) ou "s3"/"minio". A troca para S3
    # exige boto3 + bucket/credenciais via ambiente (nunca versionados); sem isso, o
    # backend S3 falha de forma clara e o local continua sendo o padrão seguro.
    storage_backend: str = "local"
    storage_s3_bucket: str | None = None
    storage_s3_endpoint_url: str | None = None  # MinIO: http://minio:9000
    storage_s3_region: str | None = None
    storage_s3_access_key: str | None = None
    storage_s3_secret_key: str | None = None
    storage_s3_prefix: str = "documents"
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o-mini"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    rag_vector_weight: float = 0.7
    rag_text_weight: float = 0.3
    rag_default_limit: int = 8
    rag_max_limit: int = 50
    rag_text_config: str = "portuguese"
    # Document Intelligence: detecção de extração insuficiente + OCR opcional (local-first).
    # ocr_enabled só tenta OCR quando um motor local estiver disponível (import-guard);
    # se indisponível, a limitação é registrada no metadata sem quebrar o pipeline.
    ocr_enabled: bool = False
    ocr_language: str = "por"
    # Limites do OCR (protegem CPU/memória da VPS): máximo de páginas por PDF e tempo por página.
    ocr_max_pages: int = 60
    ocr_page_timeout_seconds: int = 120
    # Sinais objetivos de extração insuficiente (sem número mágico único):
    # documento binário (pdf/imagem) com menos de N caracteres por página estimada,
    # ou densidade de texto muito baixa frente ao tamanho do arquivo original.
    extraction_min_chars: int = 200
    extraction_min_chars_per_kb: float = 1.0
    llm_api_key: str | None = None
    openai_api_key: str | None = None
    # ---- Resiliência da chamada ao provider LLM (configuráveis) ----
    # Timeout por chamada (s) e retries do SDK. O padrão da biblioteca seria ~600 s com
    # 2 retries, MAIOR que o proxy_read_timeout do nginx (300 s); aqui o pior caso por
    # chamada fica em (1 + retries) × timeout. max_output_tokens opcional (None = padrão
    # do modelo).
    llm_timeout_seconds: float = 90.0
    llm_max_retries: int = 1
    llm_max_output_tokens: int | None = None
    # ---- Proteção contra consumo indevido / abuso (por usuário, por processo) ----
    # Operações "críticas" são as que podem acionar LLM/embeddings/serviço externo
    # (analisar, agentes, extrair, reanalisar, reprocessar, consultar processos/débitos,
    # geocodificar). Valores justificados em docs/03-architecture/security.md.
    rate_limit_critical_per_minute: int = 10
    rate_limit_upload_per_minute: int = 30
    # Buscas de leitura que podem gerar embedding (ex.: biblioteca jurídica): bucket próprio
    # para não consumir a cota das análises; permissão continua sendo apenas ``read``.
    rate_limit_search_per_minute: int = 30
    max_concurrent_critical_per_user: int = 2
    # ---- Upload de documentos ----
    upload_max_mb: int = 30  # < client_max_body_size do nginx (50 MB)
    # Integração com a Judicial API (módulo independente consumido por HTTP).
    # URL-base, credencial e timeout vêm de ambiente/secret — nunca versionados.
    judicial_api_base_url: str = "http://judicial_api:8010"
    judicial_api_key: str | None = None
    judicial_api_timeout_seconds: float = 30.0
    # Segurança de credenciais de portal (TASK 75.1). A credencial é guardada
    # CRIPTOGRAFADA (Fernet/AES) com chave vinda de ambiente — nunca no banco nem
    # versionada. Sem a chave, o sistema recusa armazenar/revelar (falha fechada).
    # portal_admin_token protege o endpoint de recuperação (header X-Portal-Admin-Token).
    portal_secret_key: str | None = None
    portal_admin_token: str | None = None
    # Token de administração da Central de Débitos/Parâmetros (Etapa A). Protege as
    # operações administrativas (header X-Admin-Token). Falha-fechada: sem token
    # configurado, operações de ESCRITA administrativa são recusadas (503). É medida
    # PROVISÓRIA até a frente de auth/RBAC (Onda 11); NÃO substitui RBAC real.
    admin_api_token: str | None = None
    # Mapa opcional papel→token (JSON) para autorização por papel (Etapa C–F,
    # authz.py). Ex.: '{"operador":"<token>"}'. Ausente => só o papel admin
    # (admin_api_token). Provisório até auth/RBAC (Onda 11); nunca versionar tokens.
    authz_role_tokens: str | None = None
    # ---- Autenticação/RBAC real (Onda 11) ----
    # Segredo para assinar o JWT (HS256). SEM segredo configurado => emissão/validação
    # de token recusada (falha-fechada). Nunca versionar; vem do ambiente.
    jwt_secret_key: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480  # 8h; sessão expira e exige novo login
    # Bootstrap OPCIONAL do 1º usuário administrador (idempotente, via env). Sem estes
    # valores, NENHUM usuário/senha padrão é criado (sem credencial default em produção).
    auth_bootstrap_admin_email: str | None = None
    auth_bootstrap_admin_password: str | None = None
    auth_bootstrap_admin_name: str = "Administrador"
    # ---- Due Diligence integrada (4 frentes) ----
    # Integrações externas OPCIONAIS: ausência de chave => frente fica "NAO_CONFIGURADO"
    # (o sistema NUNCA simula uma consulta bem-sucedida). Todas defaultam para None,
    # de modo que o app sobe sem nenhuma delas (falha fechada por frente).
    # Google Maps Platform (geocoding/Street View/mapa). Sem a chave, a tela usa
    # apenas links externos para o Google Maps e registro manual de coordenadas.
    google_maps_api_key: str | None = None
    google_geocoding_base_url: str = "https://maps.googleapis.com/maps/api/geocode/json"
    google_maps_timeout_seconds: float = 15.0
    # Registro de imóveis eletrônico (ex.: RI Digital). Sem credencial, a matrícula
    # continua por importação manual de PDF/certidão (consulta automática indisponível).
    registro_imoveis_base_url: str | None = None
    registro_imoveis_api_key: str | None = None
    registro_imoveis_timeout_seconds: float = 30.0
    # Prefeitura/IPTU/valor venal (por município). Sem credencial/endpoint, a frente
    # funciona por cadastro manual (consulta automática indisponível).
    prefeitura_api_base_url: str | None = None
    prefeitura_api_key: str | None = None
    prefeitura_api_timeout_seconds: float = 30.0
    # Validade (horas) do cache de uma consulta externa de due diligence antes de
    # sugerir nova consulta (evita chamadas desnecessárias / custo — SPEC §12).
    due_diligence_cache_hours: int = 24
    # ---- CORS (Fase 5 — produção) ----
    # Origens permitidas (CSV). Default: origens de desenvolvimento. Em produção,
    # defina CORS_ALLOW_ORIGINS com o domínio público do frontend (ex.:
    # "https://app.exemplo.com"). Nunca usar "*" com allow_credentials=True.
    cors_allow_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in (self.cors_allow_origins or "").split(",") if o.strip()]

    @model_validator(mode="after")
    def validate_runtime(self):
        if not self.database_url.startswith("postgresql"):
            raise ValueError("O Radar exige PostgreSQL; SQLite não é suportado")
        if self.rag_vector_weight < 0 or self.rag_text_weight < 0 or self.rag_vector_weight + self.rag_text_weight <= 0:
            raise ValueError("Os pesos do ranking RAG devem ser não negativos e somar um valor maior que zero")
        if self.rag_default_limit < 1 or self.rag_max_limit < self.rag_default_limit:
            raise ValueError("Os limites do RAG são inválidos")
        return self

    @property
    def storage_path(self) -> Path:
        path = Path(self.storage_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def effective_llm_api_key(self) -> str | None:
        return self.openai_api_key or self.llm_api_key


settings = Settings()
