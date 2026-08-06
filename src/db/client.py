"""
Database client module for Supabase and PostgreSQL connections.
"""

import psycopg2
from psycopg2.extensions import connection
from supabase import create_client, Client
from src.config import SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DATABASE_URL

def get_supabase_client() -> Client:
    """
    Returns an initialized Supabase client.
    
    Returns:
        Client: Supabase client instance.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set.")
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

def get_db_connection() -> connection:
    """
    Returns a direct PostgreSQL connection via psycopg2.
    
    Returns:
        connection: psycopg2 database connection.
    """
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL must be set.")
    return psycopg2.connect(DATABASE_URL)
