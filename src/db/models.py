"""
Database models and table creation logic.
"""

from src.db.client import get_db_connection

def create_tables() -> None:
    """
    Creates necessary tables in the PostgreSQL database if they do not exist.
    """
    create_documents_sql = """
    CREATE TABLE IF NOT EXISTS documents (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        title TEXT,
        source_file TEXT,
        source_format TEXT,
        ingested_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        tags TEXT[],
        content_summary TEXT,
        chunk_count INTEGER
    );
    """
    
    create_concepts_sql = """
    CREATE TABLE IF NOT EXISTS concepts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT,
        description TEXT,
        source_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_locations_sql = """
    CREATE TABLE IF NOT EXISTS locations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        name TEXT,
        geometry_type TEXT,
        coordinates JSONB,
        properties JSONB,
        source_document_id UUID REFERENCES documents(id) ON DELETE SET NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_chunks_sql = """
    CREATE TABLE IF NOT EXISTS chunks (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
        chunk_index INTEGER,
        content TEXT,
        chunk_type TEXT,
        heading TEXT
    );
    """
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(create_documents_sql)
            cur.execute(create_concepts_sql)
            cur.execute(create_locations_sql)
            cur.execute(create_chunks_sql)
        conn.commit()
    finally:
        conn.close()
