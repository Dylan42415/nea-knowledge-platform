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
ANALYSIS_MODEL = os.getenv("ANALYSIS_MODEL", "gemini-3.5-flash-lite")
