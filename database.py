import sqlite3
import datetime
import json
from config import DATABASE_NAME

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_NAME, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        """Create necessary tables"""
        # Files table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT UNIQUE,
                file_name TEXT,
                file_size INTEGER,
                mime_type TEXT,
                caption TEXT,
                uploaded_by INTEGER,
                uploaded_at TIMESTAMP,
                download_count INTEGER DEFAULT 0,
                file_type TEXT,
                file_unique_id TEXT,
                message_id INTEGER,
                custom_link TEXT UNIQUE
            )
        ''')
        
        # Users table (tracking)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                joined_at TIMESTAMP,
                total_uploads INTEGER DEFAULT 0,
                total_downloads INTEGER DEFAULT 0
            )
        ''')
        
        # Links table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS links (
                link_id TEXT PRIMARY KEY,
                file_id TEXT,
                created_at TIMESTAMP,
                expires_at TIMESTAMP,
                created_by INTEGER,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (file_id) REFERENCES files(file_id)
            )
        ''')
        
        self.conn.commit()
    
    def add_file(self, file_id, file_name, file_size, mime_type, caption, 
                 uploaded_by, file_unique_id, message_id, file_type='document'):
        """Add new file to database"""
        try:
            self.cursor.execute('''
                INSERT INTO files 
                (file_id, file_name, file_size, mime_type, caption, uploaded_by, 
                 uploaded_at, file_unique_id, message_id, file_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                file_id, file_name, file_size, mime_type, caption, 
                uploaded_by, datetime.datetime.now(), file_unique_id, 
                message_id, file_type
            ))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            # File already exists
            return False
        except Exception as e:
            print(f"Database error: {e}")
            return False
    
    def get_file_by_custom_link(self, custom_link):
        """Get file info by custom link"""
        self.cursor.execute('''
            SELECT * FROM files WHERE custom_link = ?
        ''', (custom_link,))
        return self.cursor.fetchone()
    
    def get_file_by_file_id(self, file_id):
        """Get file info by telegram file_id"""
        self.cursor.execute('''
            SELECT * FROM files WHERE file_id = ?
        ''', (file_id,))
        return self.cursor.fetchone()
    
    def get_all_files(self, limit=50, offset=0):
        """Get all files with pagination"""
        self.cursor.execute('''
            SELECT file_id, file_name, file_size, download_count, 
                   uploaded_at, custom_link, file_type
            FROM files 
            ORDER BY uploaded_at DESC 
            LIMIT ? OFFSET ?
        ''', (limit, offset))
        return self.cursor.fetchall()
    
    def increment_download_count(self, file_id):
        """Increment download count"""
        self.cursor.execute('''
            UPDATE files SET download_count = download_count + 1 
            WHERE file_id = ?
        ''', (file_id,))
        self.conn.commit()
    
    def generate_custom_link(self, file_id, custom_name=None):
        """Generate custom link for file"""
        import random
        import string
        
        if custom_name:
            # Clean custom name for URL
            custom_name = ''.join(e for e in custom_name if e.isalnum() or e == '_')
            link_id = custom_name.lower()
        else:
            # Generate random link
            link_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
        
        # Check if link already exists
        self.cursor.execute('SELECT file_id FROM files WHERE custom_link = ?', (link_id,))
        if self.cursor.fetchone():
            # Link exists, generate new
            link_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        
        # Update file with custom link
        self.cursor.execute('''
            UPDATE files SET custom_link = ? WHERE file_id = ?
        ''', (link_id, file_id))
        self.conn.commit()
        
        return link_id
    
    def search_files(self, query):
        """Search files by name"""
        self.cursor.execute('''
            SELECT file_id, file_name, file_size, file_type 
            FROM files 
            WHERE file_name LIKE ? 
            ORDER BY uploaded_at DESC 
            LIMIT 20
        ''', (f'%{query}%',))
        return self.cursor.fetchall()
    
    def get_stats(self):
        """Get bot statistics"""
        self.cursor.execute('SELECT COUNT(*) FROM files')
        total_files = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT SUM(file_size) FROM files')
        total_size = self.cursor.fetchone()[0] or 0
        
        self.cursor.execute('SELECT SUM(download_count) FROM files')
        total_downloads = self.cursor.fetchone()[0] or 0
        
        self.cursor.execute('SELECT COUNT(DISTINCT uploaded_by) FROM files')
        total_users = self.cursor.fetchone()[0] or 0
        
        return {
            'total_files': total_files,
            'total_size': total_size,
            'total_downloads': total_downloads,
            'total_users': total_users
        }
    
    def close(self):
        """Close database connection"""
        self.conn.close()
