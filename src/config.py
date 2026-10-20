"""
Configuration module for the NEA Knowledge Management Platform.
Loads environment variables and exports constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VAULT_ROOT = PROJECT_ROOT / "ObsidianVault" / "vault"

# Vault subdirectories
DATASETS_DIR = VAULT_ROOT / "datasets"
CONCEPTS_DIR = VAULT_ROOT / "concepts"
LOCATIONS_DIR = VAULT_ROOT / "locations"
ORGANIZATIONS_DIR = VAULT_ROOT / "organizations"
TEMPLATES_DIR = VAULT_ROOT / "templates"

# Database and API configurations
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "")
ANALYSIS_MODEL = os.getenv("ANALYSIS_MODEL", "gemini-3-flash-preview")

def bootstrap_vault_archive() -> bool:
    """
    Auto-extracts ObsidianVault/vault.zip on fresh deployment if VAULT_ROOT is empty.
    Ensures fresh checkouts initialize all knowledge base notes automatically.
    """
    import zipfile
    vault_zip = PROJECT_ROOT / "ObsidianVault" / "vault.zip"
    if not VAULT_ROOT.exists() or len(list(VAULT_ROOT.rglob("*.md"))) == 0:
        if vault_zip.exists():
            VAULT_ROOT.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(vault_zip, 'r') as zf:
                zf.extractall(VAULT_ROOT)
            return True
    return False

# Execute vault archive bootstrap on config load
bootstrap_vault_archive()

