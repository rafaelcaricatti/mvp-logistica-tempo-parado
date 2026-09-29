"""Configuração da aplicação, lida de variáveis de ambiente / arquivo .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore"
    )

    # --- Identificação da API ---
    app_name: str = "ParouAí - API de Monitoramento de Tempo Parado"
    app_version: str = "1.0.0"

    # --- Firebase / Firestore ---
    # Caminho do arquivo de credenciais (service account) baixado do console Firebase.
    firebase_credentials_file: str | None = None
    # Alternativa ao arquivo: o JSON da service account inteiro em uma variável.
    firebase_credentials_json: str | None = None
    firebase_project_id: str | None = None
    # Prefixo opcional das coleções (útil para separar dev/prod no mesmo projeto).
    firestore_prefix: str = ""

    # --- Segurança (RNF04 - controle de acesso por perfil) ---
    secret_key: str = "troque-esta-chave-em-producao"
    token_expiracao_horas: int = 12
    # Credenciais do usuário administrador criado automaticamente no primeiro boot.
    admin_email: str = "admin@parouai.com"
    admin_senha: str = "admin123"

    # --- CORS ---
    cors_origins: str = "*"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
