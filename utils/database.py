import psycopg2
from psycopg2 import IntegrityError, sql
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional, Tuple

DATABASE_URL = "postgresql://postgres:*****@localhost:5432/chatbot-database"  # Update this accordingly

def create_database_if_not_exists_from_url(database_url):
    try:
        parsed_url = urlparse(database_url)
        db_name = parsed_url.path.lstrip('/')
        user = parsed_url.username
        password = parsed_url.password
        host = parsed_url.hostname
        port = parsed_url.port or 5432

        # Connect to default postgres database
        default_conn = psycopg2.connect(
            dbname='postgres',
            user=user,
            password=password,
            host=host,
            port=port
        )
        default_conn.autocommit = True
        cur = default_conn.cursor()

        # Check if database exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
        exists = cur.fetchone()

        if not exists:
            cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
            print(f"✅ Database '{db_name}' created.")
        else:
            print(f"ℹ️ Database '{db_name}' already exists.")

        cur.close()
        default_conn.close()
        return True

    except Exception as e:
        print(f"❌ Error checking/creating database: {e}")
        return False

def create_connection():
    """Create database connection with better error handling"""
    if create_database_if_not_exists_from_url(DATABASE_URL):
        try:
            conn = psycopg2.connect(DATABASE_URL)
            print("✅ Successfully connected to database")
            return conn
        except psycopg2.Error as e:
            print(f"❌ PostgreSQL connection error: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected connection error: {e}")
            return None
    else:
        print("❌ Could not ens  ure database exists.")
        return None

def init_database():
    """Initialize database tables with proper error handling"""
    conn = create_connection()

    # Check connection BEFORE using it
    if conn is None:
        print("❌ Failed to connect to database.")
        raise Exception("Database connection failed")

    try:
        cursor = conn.cursor()

        # Create tables
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            conversation_id INTEGER NOT NULL REFERENCES conversations(id),
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            user_name TEXT,  -- ADD THIS LINE
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sources (
            id SERIAL PRIMARY KEY,
            message_id INTEGER NOT NULL REFERENCES messages(id),
            source_document TEXT NOT NULL,
            page_number INTEGER,
            score REAL,
            kb_name TEXT
        );
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id SERIAL PRIMARY KEY,
            key TEXT UNIQUE NOT NULL,
            value TEXT NOT NULL
        );
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_bases (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            document_count INTEGER DEFAULT 0,
            embedding_model TEXT NOT NULL,
            chunking_strategy TEXT NOT NULL
        );
        ''')

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id SERIAL PRIMARY KEY,
            knowledge_base_id INTEGER NOT NULL REFERENCES knowledge_bases(id),
            filename TEXT NOT NULL,
            document_type TEXT NOT NULL,
            page_count INTEGER NOT NULL,
            chunk_count INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ''')

        cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    full_name TEXT,
                    email TEXT,
                    hashed_password TEXT NOT NULL,
                    disabled BOOLEAN DEFAULT FALSE
                );
                ''')

        conn.commit()
        cursor.close()
        print("✅ Database tables initialized successfully")

    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def create_user(username: str, full_name: str, email: str, hashed_password: str):
    conn = create_connection()
    if not conn:
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (username, full_name, email, hashed_password, disabled)
            VALUES (%s, %s, %s, %s, FALSE)
        """, (username, full_name, email, hashed_password))
        conn.commit()
        return True
    except psycopg2.errors.UniqueViolation:
        print("❌ Username or email already exists.")
        return False
    except Exception as e:
        print("❌ Error inserting user:", e)
        return False
    finally:
        conn.close()



def get_user_from_db(username: str):
    conn = create_connection()
    if conn is None:
        return None
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT username, full_name, email, hashed_password, disabled FROM users WHERE username = %s", (username,))
        row = cursor.fetchone()
        if row:
            return {
                "username": row[0],
                "full_name": row[1],
                "email": row[2],
                "hashed_password": row[3],
                "disabled": row[4],
            }
    except Exception as e:
        print(f"❌ Error fetching user: {e}")
    finally:
        conn.close()
    return None



def get_conversations(user_name: str = None) -> List[Tuple[int, str, str]]:
    conn = create_connection()
    cursor = conn.cursor()

    if user_name == "admin":
        # Admin sees all conversations
        cursor.execute("""
        SELECT id, title, created_at 
        FROM conversations 
        ORDER BY last_updated DESC
        """)
    elif user_name:
        # Regular users see only their conversations
        cursor.execute("""
        SELECT id, title, created_at 
        FROM conversations 
        WHERE created_by = %s 
        ORDER BY last_updated DESC
        """, (user_name,))
    else:
        # Fallback - no conversations
        return []

    conversations = cursor.fetchall()
    conn.close()
    return conversations

def create_conversation(title="New Chat", created_by: str = "admin") -> int:
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO conversations (title, created_by) 
    VALUES (%s, %s) RETURNING id
    """, (title, created_by))
    conversation_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return conversation_id

def get_messages(conversation_id: int) -> List[Tuple[int, str, str, str, str]]:
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, role, content, user_name, created_at 
    FROM messages 
    WHERE conversation_id = %s 
    ORDER BY created_at
    """, (conversation_id,))
    messages = cursor.fetchall()
    conn.close()
    return messages

def add_message(conversation_id: int, role: str, content: str, user_name: str = None) -> int:
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO messages (conversation_id, role, content, user_name) 
    VALUES (%s, %s, %s, %s) RETURNING id
    """, (conversation_id, role, content, user_name))
    message_id = cursor.fetchone()[0]
    cursor.execute("""
    UPDATE conversations 
    SET last_updated = CURRENT_TIMESTAMP 
    WHERE id = %s
    """, (conversation_id,))
    conn.commit()
    conn.close()
    return message_id

def add_sources(message_id: int, sources: List[Dict[str, Any]]) -> None:
    if not sources:
        return
    conn = create_connection()
    cursor = conn.cursor()
    for source in sources:
        try:
            score = float(source.get('score', 0.5))
        except (ValueError, TypeError):
            score = 0.5
        cursor.execute("""
        INSERT INTO sources (message_id, source_document, page_number, score, kb_name) 
        VALUES (%s, %s, %s, %s, %s)
        """, (
            message_id,
            source.get('source', ''),
            source.get('page', 0),
            score,
            source.get('kb_name', 'Unknown KB')
        ))
    conn.commit()
    conn.close()

def get_sources(message_id: int) -> List[Dict[str, Any]]:
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT source_document, page_number, score, kb_name
    FROM sources 
    WHERE message_id = %s 
    ORDER BY score DESC
    """, (message_id,))
    sources = cursor.fetchall()
    conn.close()
    return [{"source": src, "page": page, "score": score, "kb_name": kb_name} for src, page, score, kb_name in sources]

def update_conversation_title(conversation_id: int, new_title: str) -> None:
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE conversations SET title = %s WHERE id = %s", (new_title, conversation_id))
    conn.commit()
    conn.close()

def delete_conversation(conversation_id: int) -> None:
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
    DELETE FROM sources 
    WHERE message_id IN (SELECT id FROM messages WHERE conversation_id = %s)
    """, (conversation_id,))
    cursor.execute("DELETE FROM messages WHERE conversation_id = %s", (conversation_id,))
    cursor.execute("DELETE FROM conversations WHERE id = %s", (conversation_id,))
    conn.commit()
    conn.close()

def register_knowledge_base(name: str, embedding_model: str, chunking_strategy: str, description: str = "") -> int:
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO knowledge_bases (name, description, embedding_model, chunking_strategy)
        VALUES (%s, %s, %s, %s) RETURNING id
        """, (name, description, embedding_model, chunking_strategy))
        kb_id = cursor.fetchone()[0]
        conn.commit()
        return kb_id
    except psycopg2.IntegrityError:
        conn.rollback()
        cursor.execute("SELECT id FROM knowledge_bases WHERE name = %s", (name,))
        result = cursor.fetchone()
        return result[0] if result else None
    finally:
        conn.close()

def get_knowledge_bases() -> List[Dict[str, Any]]:
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, name, description, created_at, document_count, embedding_model, chunking_strategy
    FROM knowledge_bases
    ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": row[0],
            "name": row[1],
            "description": row[2],
            "created_at": row[3],
            "document_count": row[4],
            "embedding_model": row[5],
            "chunking_strategy": row[6]
        } for row in rows
    ]

def register_document(knowledge_base_id: int, filename: str, document_type: str, page_count: int, chunk_count: int) -> int:
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO documents (knowledge_base_id, filename, document_type, page_count, chunk_count)
    VALUES (%s, %s, %s, %s, %s) RETURNING id
    """, (knowledge_base_id, filename, document_type, page_count, chunk_count))
    document_id = cursor.fetchone()[0]
    cursor.execute("""
    UPDATE knowledge_bases
    SET document_count = document_count + 1
    WHERE id = %s
    """, (knowledge_base_id,))
    conn.commit()
    conn.close()
    return document_id

def get_documents(knowledge_base_id: int) -> List[Dict[str, Any]]:
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, filename, document_type, page_count, chunk_count, created_at
    FROM documents
    WHERE knowledge_base_id = %s
    ORDER BY created_at DESC
    """, (knowledge_base_id,))
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": row[0],
            "filename": row[1],
            "document_type": row[2],
            "page_count": row[3],
            "chunk_count": row[4],
            "created_at": row[5]
        } for row in rows
    ]

def get_setting(key: str, default: Any = None) -> Any:
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = %s", (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else default

def set_setting(key: str, value: Any) -> None:
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO settings (key, value) VALUES (%s, %s)
    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
    """, (key, str(value)))
    conn.commit()
    conn.close()

def get_active_knowledge_base() -> Optional[Dict[str, Any]]:
    active_kb_name = get_setting("active_knowledge_base")
    if not active_kb_name:
        return None
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, name, description, created_at, document_count, embedding_model, chunking_strategy
    FROM knowledge_bases
    WHERE name = %s
    """, (active_kb_name,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "name": row[1],
        "description": row[2],
        "created_at": row[3],
        "document_count": row[4],
        "embedding_model": row[5],
        "chunking_strategy": row[6]
    }

def set_active_knowledge_base(kb_name: str) -> None:
    set_setting("active_knowledge_base", kb_name)


# def migrate_add_created_by_column():
#     """Add created_by column if it doesn't exist"""
#     conn = create_connection()
#     cursor = conn.cursor()
#     try:
#         cursor.execute("""
#         SELECT column_name
#         FROM information_schema.columns
#         WHERE table_name='conversations' AND column_name='created_by';
#         """)
#
#         if not cursor.fetchone():
#             cursor.execute("ALTER TABLE conversations ADD COLUMN created_by TEXT;")
#             # Set existing conversations to 'admin' as default
#             cursor.execute("UPDATE conversations SET created_by = 'admin' WHERE created_by IS NULL;")
#             conn.commit()
#             print("✅ Added created_by column to conversations table")
#         else:
#             print("ℹ️ created_by column already exists")
#
#     except Exception as e:
#         print(f"❌ Error adding created_by column: {e}")
#         conn.rollback()
#     finally:
#         cursor.close()
#         conn.close()

if __name__=="__main__":
    init_database()