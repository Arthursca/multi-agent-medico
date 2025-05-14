# pipeline/db.py  (ou onde você definiu engine)
from sqlalchemy import text
from sqlalchemy import create_engine, event
from pgvector.psycopg2 import register_vector
from app.config import DATABASE_URL, EMBEDDING_DIM
from app.agents.health_plan_agent.tools.rag.utils.logger import get_logger

logger = get_logger(__name__)

engine = create_engine(DATABASE_URL, echo=False)

@event.listens_for(engine, "connect")
def _register_vector(dbapi_conn, connection_record):
    # Mapeia automaticamente Python List[float] → pgvector VECTOR
    register_vector(dbapi_conn)

def init_db() -> None:
    logger.info("Inicializando schema do vectorstore")
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.execute(text(f"""
            CREATE TABLE IF NOT EXISTS docs (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                metadata JSONB,
                embedding VECTOR({EMBEDDING_DIM})
            );
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS docs_embedding_hnsw_idx
            ON docs USING hnsw (embedding)
        """))
    logger.info("Schema inicializado com sucesso")
