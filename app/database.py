"""
Database module - Updated to use in-memory cache instead of SQLite
"""
from app.cache import get_cache

# Dependency to get cache instance
def get_db():
    return get_cache()

# Create tables function is no longer needed for in-memory cache
def create_tables():
    pass
