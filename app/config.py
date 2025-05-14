"""
utils/config.py

Centraliza o carregamento e acesso às configurações sensíveis da aplicação.
Carrega variáveis de ambiente definidas no arquivo .env usando python-dotenv no startup da aplicação.
Expondo configurações como:
- URL de conexão com Postgres+pgvector
- Diretório de dados de ingestão
- Parâmetros de chunking (tamanho e sobreposição)
- Provedor de LLM e chaves de API
- Nível de log e flags de tracing
"""
import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()

# URL de conexão com o banco de dados Postgres (incluindo pgvector)
# Exemplo: postgres://user:password@localhost:5432/dbname
DATABASE_URL: str = os.getenv("DATABASE_URL", "")

# Diretório base para ingestão de documentos
# Padrão: 'data/'
DATA_DIR: str = os.getenv("DATA_DIR", "data")

# Configurações de chunking
# Tamanho máximo de cada chunk (número de caracteres)
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
# Sobreposição entre chunks consecutivos
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))

# Provedor de LLM selecionado (por exemplo, "openai", "anthropic" ou "gemini")
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")

# Chaves de API para provedores de LLM suportados
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

EMBEDDING_DIM: str = os.getenv("EMBEDDING_DIM", 1536)

# Nível de log padrão para a aplicação (ex.: "DEBUG", "INFO", "WARNING", "ERROR")
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# Flags para habilitar tracing e monitoramento
# Habilita tracing customizado (uso geral)
ENABLE_TRACING: bool = os.getenv("ENABLE_TRACING", "false").lower() in ("true", "1", "yes")
# Habilita o tracing integrado do LangChain via LangSmith
LANGSMITH_TRACING: bool = os.getenv("LANGSMITH_TRACING", "false").lower() in ("true", "1", "yes")

# Chave para LangSmith
LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", "")

LANGSMITH_PROJECT: str = os.getenv("LANSMITH_PROJECT", "")

class Settings:
    """
    Wrapper para acesso às configurações principais.
    """
    def __init__(self) -> None:
        # Diretório de ingestão de dados
        self.DATA_DIR: str = DATA_DIR

# Exporta instância de settings para compatibilidade com módulos que importam 'settings'
settings = Settings()
