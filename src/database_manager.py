"""
Database Manager for AI Support Agent
Handles database connections and data management for knowledge files.
"""

import sqlite3
import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, List, Optional, Any, Union
import os
import json
import logging
from pathlib import Path
from datetime import datetime

# Optional imports for database drivers
try:
    import psycopg2
    has_postgresql = True
except ImportError:
    has_postgresql = False

try:
    import mysql.connector
    has_mysql = True
except ImportError:
    has_mysql = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations for knowledge files."""
    
    def __init__(self):
        self.connection = None
        self.engine = None
        self.db_type = None
        self.connection_params = {}
        
    def connect_sqlite(self, db_path: str) -> bool:
        """Connect to SQLite database."""
        try:
            self.connection = sqlite3.connect(db_path)
            self.db_type = "sqlite"
            self.connection_params = {"db_path": db_path}
            logger.info(f"Connected to SQLite database: {db_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to SQLite database: {e}")
            return False
    
    def connect_postgresql(self, host: str, port: int, database: str, 
                          username: str, password: str) -> bool:
        """Connect to PostgreSQL database."""
        try:
            connection_string = f"postgresql://{username}:{password}@{host}:{port}/{database}"
            self.engine = create_engine(connection_string)
            
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                
            self.db_type = "postgresql"
            self.connection_params = {
                "host": host,
                "port": port,
                "database": database,
                "username": username,
                "password": password
            }
            logger.info(f"Connected to PostgreSQL database: {host}:{port}/{database}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL database: {e}")
            return False
    
    def connect_mysql(self, host: str, port: int, database: str, 
                     username: str, password: str) -> bool:
        """Connect to MySQL database."""
        try:
            connection_string = f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
            self.engine = create_engine(connection_string)
            
            # Test connection
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
                
            self.db_type = "mysql"
            self.connection_params = {
                "host": host,
                "port": port,
                "database": database,
                "username": username,
                "password": password
            }
            logger.info(f"Connected to MySQL database: {host}:{port}/{database}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MySQL database: {e}")
            return False
    
    def test_connection(self) -> bool:
        """Test the current database connection."""
        try:
            if self.db_type == "sqlite" and self.connection:
                cursor = self.connection.cursor()
                cursor.execute("SELECT 1")
                return True
            elif self.engine:
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                return True
            return False
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_tables(self) -> List[str]:
        """Get list of tables in the database."""
        try:
            if self.db_type == "sqlite" and self.connection:
                cursor = self.connection.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                return [row[0] for row in cursor.fetchall()]
            elif self.engine:
                inspector = inspect(self.engine)
                return inspector.get_table_names()
            return []
        except Exception as e:
            logger.error(f"Failed to get tables: {e}")
            return []
    
    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """Get columns information for a specific table."""
        try:
            if self.db_type == "sqlite" and self.connection:
                cursor = self.connection.cursor()
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = []
                for row in cursor.fetchall():
                    columns.append({
                        "name": row[1],
                        "type": row[2],
                        "nullable": not row[3],
                        "primary_key": bool(row[5])
                    })
                return columns
            elif self.engine:
                inspector = inspect(self.engine)
                columns = inspector.get_columns(table_name)
                return [
                    {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col["nullable"],
                        "primary_key": col.get("primary_key", False)
                    }
                    for col in columns
                ]
            return []
        except Exception as e:
            logger.error(f"Failed to get table columns: {e}")
            return []
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
        """Execute a SQL query and return results as DataFrame."""
        try:
            if self.db_type == "sqlite" and self.connection:
                return pd.read_sql_query(query, self.connection, params=params)
            elif self.engine:
                return pd.read_sql_query(query, self.engine, params=params)
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            return pd.DataFrame()
    
    def upload_dataframe(self, df: pd.DataFrame, table_name: str, 
                        if_exists: str = "replace") -> bool:
        """Upload a DataFrame to the database."""
        try:
            if self.db_type == "sqlite" and self.connection:
                df.to_sql(table_name, self.connection, if_exists=if_exists, index=False)
            elif self.engine:
                df.to_sql(table_name, self.engine, if_exists=if_exists, index=False)
            else:
                return False
            
            logger.info(f"Successfully uploaded {len(df)} rows to table '{table_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to upload DataFrame: {e}")
            return False
    
    def upload_csv(self, csv_path: str, table_name: str, 
                   if_exists: str = "replace") -> bool:
        """Upload a CSV file to the database."""
        try:
            df = pd.read_csv(csv_path)
            return self.upload_dataframe(df, table_name, if_exists)
        except Exception as e:
            logger.error(f"Failed to upload CSV: {e}")
            return False
    
    def export_to_csv(self, query: str, output_path: str) -> bool:
        """Export query results to CSV file."""
        try:
            df = self.execute_query(query)
            if not df.empty:
                df.to_csv(output_path, index=False)
                logger.info(f"Exported {len(df)} rows to {output_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            return False
    
    def get_knowledge_documents(self, limit: int = 100) -> pd.DataFrame:
        """Get knowledge documents from database."""
        try:
            # Try common knowledge table names
            tables = self.get_tables()
            knowledge_tables = [t for t in tables if any(
                keyword in t.lower() for keyword in ['knowledge', 'document', 'content', 'article']
            )]
            
            if not knowledge_tables:
                return pd.DataFrame()
                
            # Use the first matching table
            table_name = knowledge_tables[0]
            query = f"SELECT * FROM {table_name} LIMIT {limit}"
            return self.execute_query(query)
        except Exception as e:
            logger.error(f"Failed to get knowledge documents: {e}")
            return pd.DataFrame()
    
    def save_connection_config(self, config_name: str) -> bool:
        """Save current connection configuration."""
        try:
            config = {
                "db_type": self.db_type,
                "connection_params": self.connection_params,
                "created_at": datetime.now().isoformat()
            }
            
            config_dir = Path("database_configs")
            config_dir.mkdir(exist_ok=True)
            
            config_path = config_dir / f"{config_name}.json"
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Saved connection config: {config_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save connection config: {e}")
            return False
    
    def load_connection_config(self, config_name: str) -> bool:
        """Load and connect using saved configuration."""
        try:
            config_path = Path("database_configs") / f"{config_name}.json"
            
            if not config_path.exists():
                logger.error(f"Config file not found: {config_name}")
                return False
            
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            db_type = config["db_type"]
            params = config["connection_params"]
            
            if db_type == "sqlite":
                return self.connect_sqlite(params["db_path"])
            elif db_type == "postgresql":
                return self.connect_postgresql(
                    params["host"], params["port"], params["database"],
                    params["username"], params["password"]
                )
            elif db_type == "mysql":
                return self.connect_mysql(
                    params["host"], params["port"], params["database"],
                    params["username"], params["password"]
                )
            
            return False
        except Exception as e:
            logger.error(f"Failed to load connection config: {e}")
            return False
    
    def get_saved_configs(self) -> List[str]:
        """Get list of saved connection configurations."""
        try:
            config_dir = Path("database_configs")
            if not config_dir.exists():
                return []
            
            configs = []
            for file_path in config_dir.glob("*.json"):
                configs.append(file_path.stem)
            
            return configs
        except Exception as e:
            logger.error(f"Failed to get saved configs: {e}")
            return []
    
    def close(self):
        """Close database connection."""
        try:
            if self.connection:
                self.connection.close()
                self.connection = None
            if self.engine:
                self.engine.dispose()
                self.engine = None
            self.db_type = None
            self.connection_params = {}
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
    
    def __del__(self):
        """Cleanup on object destruction."""
        self.close() 