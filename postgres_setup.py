"""
Setup script for PostgreSQL with pgvector for RAG Chatbot.
This script helps you set up the database and verify the installation.
"""

import psycopg2
import psycopg2.extras
import logging
import sys
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("setup")

# Database connection string
DATABASE_URL = "postgresql://postgres:Kkiraak1234@localhost/rag-chatbot"


def test_connection():
    """Test the PostgreSQL connection."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        logger.info(f"Successfully connected to PostgreSQL: {version}")
        cursor.close()
        conn.close()
        return True
    except psycopg2.Error as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        return False


def check_pgvector_extension():
    """Check if pgvector extension is available."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Check if pgvector extension is available
        cursor.execute("""
        SELECT name FROM pg_available_extensions WHERE name = 'vector'
        """)
        result = cursor.fetchone()

        if result:
            logger.info("pgvector extension is available")

            # Check if it's already enabled
            cursor.execute("""
            SELECT extname FROM pg_extension WHERE extname = 'vector'
            """)
            enabled = cursor.fetchone()

            if enabled:
                logger.info("pgvector extension is already enabled")
            else:
                logger.info("pgvector extension is available but not enabled")

            cursor.close()
            conn.close()
            return True
        else:
            logger.error("pgvector extension is not available")
            logger.error("Please install pgvector extension first")
            cursor.close()
            conn.close()
            return False

    except psycopg2.Error as e:
        logger.error(f"Error checking pgvector extension: {e}")
        return False


def enable_pgvector_extension():
    """Enable the pgvector extension."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Enable pgvector extension
        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit()

        logger.info("pgvector extension enabled successfully")

        # Test vector functionality
        cursor.execute("SELECT '[1,2,3]'::vector")
        result = cursor.fetchone()[0]
        logger.info(f"Vector test successful: {result}")

        cursor.close()
        conn.close()
        return True

    except psycopg2.Error as e:
        logger.error(f"Error enabling pgvector extension: {e}")
        return False


def setup_database():
    """Set up the complete database schema."""
    try:
        # Import the database initialization function
        from utils.database import init_database

        logger.info("Setting up database schema...")
        init_database()
        logger.info("Database schema setup completed successfully")
        return True

    except Exception as e:
        logger.error(f"Error setting up database schema: {e}")
        return False


def verify_setup():
    """Verify the complete setup."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Check if all tables exist
        tables_to_check = [
            'conversations', 'messages', 'sources', 'settings',
            'knowledge_bases', 'documents', 'document_chunks'
        ]

        for table in tables_to_check:
            cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            )
            """, (table,))
            exists = cursor.fetchone()[0]

            if exists:
                logger.info(f"✓ Table '{table}' exists")
            else:
                logger.error(f"✗ Table '{table}' does not exist")
                cursor.close()
                conn.close()
                return False

        # Check if vector column exists in document_chunks
        cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'document_chunks' 
        AND column_name = 'embedding'
        """)
        result = cursor.fetchone()

        if result and 'USER-DEFINED' in result[1]:  # vector type shows as USER-DEFINED
            logger.info("✓ Vector embedding column exists and is properly typed")
        else:
            logger.error("✗ Vector embedding column not found or incorrectly typed")
            cursor.close()
            conn.close()
            return False

        # Check vector indices
        cursor.execute("""
        SELECT indexname FROM pg_indexes 
        WHERE tablename = 'document_chunks' 
        AND indexname LIKE '%embedding%'
        """)
        indices = cursor.fetchall()

        if indices:
            logger.info(f"✓ Found {len(indices)} vector indices")
            for idx in indices:
                logger.info(f"  - {idx[0]}")
        else:
            logger.warning("⚠ No vector indices found (they will be created automatically)")

        cursor.close()
        conn.close()
        logger.info("✓ Database verification completed successfully")
        return True

    except psycopg2.Error as e:
        logger.error(f"Error during verification: {e}")
        return False


def get_database_info():
    """Get information about the database setup."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()

        info = {}

        # Get PostgreSQL version
        cursor.execute("SELECT version()")
        info['postgresql_version'] = cursor.fetchone()[0]

        # Get pgvector version
        cursor.execute("""
        SELECT installed_version FROM pg_available_extensions 
        WHERE name = 'vector'
        """)
        result = cursor.fetchone()
        info['pgvector_available'] = result[0] if result else 'Not available'

        # Check if extension is enabled
        cursor.execute("""
        SELECT extversion FROM pg_extension WHERE extname = 'vector'
        """)
        result = cursor.fetchone()
        info['pgvector_enabled'] = result[0] if result else 'Not enabled'

        # Get table counts
        for table in ['conversations', 'messages', 'knowledge_bases', 'documents', 'document_chunks']:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                info[f'{table}_count'] = cursor.fetchone()[0]
            except psycopg2.Error:
                info[f'{table}_count'] = 'Table not found'

        cursor.close()
        conn.close()

        return info

    except psycopg2.Error as e:
        logger.error(f"Error getting database info: {e}")
        return {}


def main():
    """Main setup function."""
    logger.info("Starting PostgreSQL with pgvector setup...")

    # Step 1: Test connection
    logger.info("Step 1: Testing PostgreSQL connection...")
    if not test_connection():
        logger.error("Cannot connect to PostgreSQL. Please check your connection settings.")
        sys.exit(1)

    # Step 2: Check pgvector availability
    logger.info("Step 2: Checking pgvector extension...")
    if not check_pgvector_extension():
        logger.error("pgvector extension is not available. Please install it first.")
        logger.info("Installation instructions:")
        logger.info("1. For Ubuntu/Debian: apt install postgresql-14-pgvector")
        logger.info("2. For macOS with Homebrew: brew install pgvector")
        logger.info("3. For other systems, see: https://github.com/pgvector/pgvector")
        sys.exit(1)

    # Step 3: Enable pgvector extension
    logger.info("Step 3: Enabling pgvector extension...")
    if not enable_pgvector_extension():
        logger.error("Failed to enable pgvector extension.")
        sys.exit(1)

    # Step 4: Setup database schema
    logger.info("Step 4: Setting up database schema...")
    if not setup_database():
        logger.error("Failed to setup database schema.")
        sys.exit(1)

    # Step 5: Verify setup
    logger.info("Step 5: Verifying setup...")
    if not verify_setup():
        logger.error("Setup verification failed.")
        sys.exit(1)

    # Step 6: Display information
    logger.info("Step 6: Getting database information...")
    info = get_database_info()

    logger.info("\n" + "=" * 50)
    logger.info("SETUP COMPLETED SUCCESSFULLY!")
    logger.info("=" * 50)
    logger.info(f"PostgreSQL Version: {info.get('postgresql_version', 'Unknown')}")
    logger.info(f"pgvector Available: {info.get('pgvector_available', 'Unknown')}")
    logger.info(f"pgvector Enabled: {info.get('pgvector_enabled', 'Unknown')}")
    logger.info("\nTable Counts:")
    for key, value in info.items():
        if key.endswith('_count'):
            table_name = key.replace('_count', '').replace('_', ' ').title()
            logger.info(f"  {table_name}: {value}")

    logger.info("\nYour RAG Chatbot is now ready to use PostgreSQL with pgvector!")
    logger.info("You can now run your application and upload documents.")


if __name__ == "__main__":
    main()