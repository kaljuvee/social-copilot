import sqlite3
import pandas as pd
from datetime import datetime
from typing import Optional, List
import os

DATABASE_PATH = os.getenv('DATABASE_PATH', 'social_media_posts.db')

def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    # Posts table
    c.execute('''CREATE TABLE IF NOT EXISTS posts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  content TEXT NOT NULL,
                  platforms TEXT NOT NULL,
                  scheduled_time TEXT,
                  status TEXT DEFAULT 'draft',
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                  error_message TEXT)''')
    
    # API credentials table
    c.execute('''CREATE TABLE IF NOT EXISTS api_credentials
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  platform TEXT UNIQUE NOT NULL,
                  credentials TEXT NOT NULL,
                  created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    
    # Post queue for rate limiting
    c.execute('''CREATE TABLE IF NOT EXISTS post_queue
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  post_id INTEGER,
                  platform TEXT,
                  status TEXT DEFAULT 'pending',
                  retry_count INTEGER DEFAULT 0,
                  last_attempt TEXT,
                  FOREIGN KEY(post_id) REFERENCES posts(id))''')
    
    conn.commit()
    conn.close()

def save_post(content: str, platforms: str, scheduled_time: Optional[str] = None, 
              status: str = 'draft', error_message: Optional[str] = None) -> int:
    """Save a post to the database and return the post ID"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    c.execute('''INSERT INTO posts (content, platforms, scheduled_time, status, error_message)
                 VALUES (?, ?, ?, ?, ?)''',
              (content, platforms, scheduled_time, status, error_message))
    
    post_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return post_id

def get_posts() -> pd.DataFrame:
    """Retrieve all posts from database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        df = pd.read_sql_query(
            "SELECT * FROM posts ORDER BY created_at DESC", 
            conn
        )
        conn.close()
        return df
    except Exception as e:
        print(f"Error retrieving posts: {e}")
        return pd.DataFrame()

def get_failed_posts() -> pd.DataFrame:
    """Retrieve failed posts from database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        df = pd.read_sql_query(
            "SELECT * FROM posts WHERE status = 'failed' ORDER BY created_at DESC", 
            conn
        )
        conn.close()
        return df
    except Exception as e:
        print(f"Error retrieving failed posts: {e}")
        return pd.DataFrame()

def get_scheduled_posts() -> pd.DataFrame:
    """Retrieve scheduled posts from database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        df = pd.read_sql_query(
            "SELECT * FROM posts WHERE status = 'scheduled' ORDER BY scheduled_time ASC", 
            conn
        )
        conn.close()
        return df
    except Exception as e:
        print(f"Error retrieving scheduled posts: {e}")
        return pd.DataFrame()

def update_post_status(post_id: int, status: str, error_message: Optional[str] = None):
    """Update post status"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    if error_message:
        c.execute("UPDATE posts SET status = ?, error_message = ? WHERE id = ?", 
                  (status, error_message, post_id))
    else:
        c.execute("UPDATE posts SET status = ? WHERE id = ?", (status, post_id))
    
    conn.commit()
    conn.close()

def delete_post(post_id: int):
    """Delete a post and related queue entries"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    # Delete from queue first
    c.execute("DELETE FROM post_queue WHERE post_id = ?", (post_id,))
    
    # Delete the post
    c.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    
    conn.commit()
    conn.close()

def get_post_by_id(post_id: int) -> Optional[dict]:
    """Get a specific post by ID"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    c.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
    row = c.fetchone()
    
    conn.close()
    
    if row:
        columns = ['id', 'content', 'platforms', 'scheduled_time', 'status', 'created_at', 'error_message']
        return dict(zip(columns, row))
    
    return None

def save_api_credentials(platform: str, credentials: str):
    """Save API credentials for a platform"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    c.execute('''INSERT OR REPLACE INTO api_credentials (platform, credentials)
                 VALUES (?, ?)''',
              (platform, credentials))
    
    conn.commit()
    conn.close()

def get_api_credentials(platform: str) -> Optional[str]:
    """Get API credentials for a platform"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    c.execute("SELECT credentials FROM api_credentials WHERE platform = ?", (platform,))
    row = c.fetchone()
    
    conn.close()
    
    return row[0] if row else None

def add_to_queue(post_id: int, platform: str):
    """Add a post to the platform-specific queue"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    c.execute('''INSERT INTO post_queue (post_id, platform, status)
                 VALUES (?, ?, 'pending')''',
              (post_id, platform))
    
    conn.commit()
    conn.close()

def get_queue_items(platform: str, limit: int = 10) -> pd.DataFrame:
    """Get pending queue items for a platform"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        df = pd.read_sql_query(
            """SELECT pq.*, p.content, p.platforms 
               FROM post_queue pq
               JOIN posts p ON pq.post_id = p.id
               WHERE pq.platform = ? AND pq.status = 'pending'
               ORDER BY pq.id ASC
               LIMIT ?""", 
            conn, params=(platform, limit)
        )
        conn.close()
        return df
    except Exception as e:
        print(f"Error retrieving queue items: {e}")
        return pd.DataFrame()

def update_queue_status(queue_id: int, status: str, retry_count: int = None):
    """Update queue item status"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    if retry_count is not None:
        c.execute('''UPDATE post_queue 
                     SET status = ?, retry_count = ?, last_attempt = CURRENT_TIMESTAMP 
                     WHERE id = ?''',
                  (status, retry_count, queue_id))
    else:
        c.execute('''UPDATE post_queue 
                     SET status = ?, last_attempt = CURRENT_TIMESTAMP 
                     WHERE id = ?''',
                  (status, queue_id))
    
    conn.commit()
    conn.close()

def clean_old_posts(days_old: int = 30):
    """Clean up old completed/failed posts"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    c.execute('''DELETE FROM posts 
                 WHERE status IN ('posted', 'failed') 
                 AND datetime(created_at) < datetime('now', '-{} days')'''.format(days_old))
    
    conn.commit()
    conn.close()