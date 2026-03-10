import os
import redis
import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver
from dotenv import load_dotenv

# Load env vars
load_dotenv()

class DatabaseManager:
    _instance = None
    
    def __init__(self):
        # Database Paths
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.base_dir, "data")
        self.db_path = os.path.join(self.data_dir, "memory.db")
        
        # Ensure data directory exists
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            print(f"[DB] Created data directory: {self.data_dir}")
            
        self.checkpointer = None
        
        # Redis Config
        self.redis_host = os.getenv("REDIS_HOST", "localhost")
        self.redis_port = int(os.getenv("REDIS_PORT", 6379))
        self.redis_client = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = DatabaseManager()
        return cls._instance

    def get_checkpointer(self):
        if self.checkpointer is None:
            try:
                # Use a persistent connection for SQLite
                # Use a persistent connection for SQLite with increased timeout for concurrency
                conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30.0)
                conn.execute("PRAGMA journal_mode=WAL")
                self.checkpointer = SqliteSaver(conn)
                
                # Initialize Layer 4 Memories table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_memories (
                        user_id TEXT,
                        key TEXT,
                        value TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, key)
                    )
                """)
                
                # Tasks / TODO list table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        deadline TEXT,
                        done INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # ── Expense Tracking Tables ──────────────────────
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS accounts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        type TEXT DEFAULT 'bank',
                        balance REAL DEFAULT 0.0,
                        UNIQUE(user_id, name)
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        type TEXT NOT NULL CHECK(type IN ('income','expense','transfer')),
                        amount REAL NOT NULL,
                        category TEXT,
                        description TEXT,
                        account_id INTEGER,
                        to_account_id INTEGER,
                        date TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(account_id) REFERENCES accounts(id),
                        FOREIGN KEY(to_account_id) REFERENCES accounts(id)
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        type TEXT DEFAULT 'expense' CHECK(type IN ('income','expense')),
                        UNIQUE(user_id, name)
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS debts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        person TEXT NOT NULL,
                        amount REAL NOT NULL,
                        direction TEXT NOT NULL CHECK(direction IN ('owe','owed')),
                        description TEXT,
                        settled INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # Seed default accounts
                default_accounts = [
                    ("local_user", "Union Bank", "bank"),
                    ("local_user", "SBI", "bank"),
                    ("local_user", "Saraswat", "bank"),
                    ("local_user", "Cash", "cash"),
                ]
                for uid, name, atype in default_accounts:
                    conn.execute(
                        "INSERT OR IGNORE INTO accounts (user_id, name, type) VALUES (?, ?, ?)",
                        (uid, name, atype)
                    )

                # Seed default categories
                default_categories = [
                    ("local_user", "Food", "expense"),
                    ("local_user", "Rent", "expense"),
                    ("local_user", "Transport", "expense"),
                    ("local_user", "Shopping", "expense"),
                    ("local_user", "Entertainment", "expense"),
                    ("local_user", "Bills", "expense"),
                    ("local_user", "Health", "expense"),
                    ("local_user", "Education", "expense"),
                    ("local_user", "Other", "expense"),
                    ("local_user", "Salary", "income"),
                    ("local_user", "Freelance", "income"),
                    ("local_user", "Investment", "income"),
                ]
                for uid, name, ctype in default_categories:
                    conn.execute(
                        "INSERT OR IGNORE INTO categories (user_id, name, type) VALUES (?, ?, ?)",
                        (uid, name, ctype)
                    )
                conn.commit()
                
                print(f"[DB] SQLite checkpointer and memories initialized at {self.db_path}")
            except Exception as e:
                print(f"[ERROR] Failed to initialize SQLite checkpointer: {e}")
                return None
        return self.checkpointer

    def get_redis(self):
        if self.redis_client is None:
            print(f"[DB] Initializing Redis client: {self.redis_host}:{self.redis_port}")
            self.redis_client = redis.Redis(
                host=self.redis_host, 
                port=self.redis_port, 
                decode_responses=True
            )
        return self.redis_client

db_manager = DatabaseManager.get_instance()
