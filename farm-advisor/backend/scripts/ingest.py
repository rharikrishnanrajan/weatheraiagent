import sys
import logging
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.rag.ingest import ingest_documents
from app.db.session import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ingest_script")

def main():
    logger.info("Initializing database...")
    init_db()
    logger.info("Starting ingestion of farming knowledge base...")
    res = ingest_documents()
    logger.info("Ingestion complete: %s", res)

if __name__ == "__main__":
    main()
