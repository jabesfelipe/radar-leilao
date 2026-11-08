"""Backend de storage S3/MinIO (Fase 4) — produção.

Import-guarded: só exige ``boto3`` quando o backend S3 é efetivamente selecionado.
NÃO cria bucket nem contrata serviço: usa o bucket/endpoint já configurados via
ambiente. Compatível com MinIO (endpoint_url) e S3 (sem endpoint_url).

Configuração (via settings/ambiente, NUNCA versionada):
  storage_backend = "s3" | "minio"
  storage_s3_bucket, storage_s3_endpoint_url (opcional p/ MinIO),
  storage_s3_region, storage_s3_access_key, storage_s3_secret_key,
  storage_s3_prefix (prefixo de chave, ex.: "documents/").
"""
from __future__ import annotations

from .base import DocumentStorage, StoredObject


class S3Storage(DocumentStorage):
    def __init__(self, settings):
        try:
            import boto3  # noqa: F401
        except Exception as exc:  # pragma: no cover - ambiente sem boto3
            raise RuntimeError(
                "storage_backend=s3 requer 'boto3' instalado. Instale boto3 ou use storage_backend=local."
            ) from exc
        import boto3

        self.bucket = getattr(settings, "storage_s3_bucket", None)
        if not self.bucket:
            raise RuntimeError("storage_s3_bucket não configurado para o backend S3.")
        self.prefix = (getattr(settings, "storage_s3_prefix", "") or "").strip("/")
        self.endpoint_url = getattr(settings, "storage_s3_endpoint_url", None) or None
        self._client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            region_name=getattr(settings, "storage_s3_region", None) or None,
            aws_access_key_id=getattr(settings, "storage_s3_access_key", None) or None,
            aws_secret_access_key=getattr(settings, "storage_s3_secret_key", None) or None,
        )

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}/{key}".lstrip("/") if self.prefix else key

    def write_bytes(self, key: str, data: bytes) -> StoredObject:
        self._client.put_object(Bucket=self.bucket, Key=self._full_key(key), Body=data)
        return StoredObject(key=key, uri=self.uri_for(key), size=len(data))

    def write_text(self, key: str, text: str, encoding: str = "utf-8") -> StoredObject:
        return self.write_bytes(key, text.encode(encoding))

    def read_bytes(self, key: str) -> bytes:
        obj = self._client.get_object(Bucket=self.bucket, Key=self._full_key(key))
        return obj["Body"].read()

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=self._full_key(key))
            return True
        except Exception:
            return False

    def uri_for(self, key: str) -> str:
        return f"s3://{self.bucket}/{self._full_key(key)}"

    def backend_name(self) -> str:
        return "minio" if self.endpoint_url else "s3"
