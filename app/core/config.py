from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr
class Settings(BaseSettings):
    app_name: str ="Document Q&A RAG"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str
    max_document_size_mb: int = 20

    allowed_document_extensions: list[str] = [
        ".pdf",
        ".docx",
        ".txt",
    ]
    storage_dir: str = "storage/documents"
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


    # Embedding model
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dimensions: int = 384
    embedding_batch_size: int = 32

    # Token-aware chunking
    chunk_size_tokens: int = 400
    max_chunk_size_tokens: int = 500
    chunk_overlap_tokens: int = 60

    # Groq LLM
    groq_api_key: SecretStr | None = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_timeout_seconds: float = 30.0
    groq_max_completion_tokens: int = 800
    groq_temperature: float = 0.1






    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings=Settings()