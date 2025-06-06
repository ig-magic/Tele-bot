import sqlite3
import json
from datetime import datetime

class Database:
    def __init__(self, db_file="bot_data.db"):
        self.db_file = db_file
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()

        # Create tables
        c.execute('''CREATE TABLE IF NOT EXISTS group_settings
                    (group_id INTEGER PRIMARY KEY,
                     welcome_message TEXT,
                     rules TEXT,
                     settings TEXT)''')

        c.execute('''CREATE TABLE IF NOT EXISTS user_data
                    (user_id INTEGER PRIMARY KEY,
                     warnings INTEGER DEFAULT 0,
                     is_banned BOOLEAN DEFAULT 0,
                     join_date TEXT,
                     notes TEXT,
                     language TEXT DEFAULT 'en',
                     notification_settings TEXT)''')

        c.execute('''CREATE TABLE IF NOT EXISTS chat_messages
                    (message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                     chat_id INTEGER,
                     user_id INTEGER,
                     message_type TEXT,
                     message_date TEXT,
                     content TEXT)''')

        # New tables for enhanced features
        c.execute('''CREATE TABLE IF NOT EXISTS notes
                    (note_id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id INTEGER,
                     group_id INTEGER,
                     title TEXT,
                     content TEXT,
                     created_at TEXT,
                     updated_at TEXT)''')

        c.execute('''CREATE TABLE IF NOT EXISTS tags
                    (tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                     name TEXT,
                     group_id INTEGER)''')

        c.execute('''CREATE TABLE IF NOT EXISTS note_tags
                    (note_id INTEGER,
                     tag_id INTEGER,
                     FOREIGN KEY(note_id) REFERENCES notes(note_id),
                     FOREIGN KEY(tag_id) REFERENCES tags(tag_id))''')

        c.execute('''CREATE TABLE IF NOT EXISTS reminders
                    (reminder_id INTEGER PRIMARY KEY AUTOINCREMENT,
                     user_id INTEGER,
                     group_id INTEGER,
                     content TEXT,
                     remind_at TEXT,
                     created_at TEXT,
                     is_completed BOOLEAN DEFAULT 0)''')

        c.execute('''CREATE TABLE IF NOT EXISTS user_preferences
                    (user_id INTEGER PRIMARY KEY,
                     theme TEXT DEFAULT 'light',
                     timezone TEXT DEFAULT 'UTC',
                     notification_preferences TEXT)''')

        conn.commit()
        conn.close()

    def set_welcome_message(self, group_id: int, message: str):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO group_settings (group_id, welcome_message) VALUES (?, ?)',
                 (group_id, message))
        conn.commit()
        conn.close()

    def get_welcome_message(self, group_id: int) -> str:
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('SELECT welcome_message FROM group_settings WHERE group_id = ?', (group_id,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def set_rules(self, group_id: int, rules: str):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO group_settings (group_id, rules) VALUES (?, ?)',
                 (group_id, rules))
        conn.commit()
        conn.close()

    def get_rules(self, group_id: int) -> str:
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('SELECT rules FROM group_settings WHERE group_id = ?', (group_id,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None

    def add_warning(self, user_id: int) -> int:
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO user_data (user_id, warnings) \
                  VALUES (?, COALESCE((SELECT warnings + 1 FROM user_data WHERE user_id = ?), 1))',
                 (user_id, user_id))
        c.execute('SELECT warnings FROM user_data WHERE user_id = ?', (user_id,))
        warnings = c.fetchone()[0]
        conn.commit()
        conn.close()
        return warnings

    def remove_warning(self, user_id: int) -> int:
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('UPDATE user_data SET warnings = warnings - 1 WHERE user_id = ? AND warnings > 0',
                 (user_id,))
        c.execute('SELECT warnings FROM user_data WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        warnings = result[0] if result else 0
        conn.commit()
        conn.close()
        return warnings

    def set_ban_status(self, user_id: int, is_banned: bool):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO user_data (user_id, is_banned) VALUES (?, ?)',
                 (user_id, is_banned))
        conn.commit()
        conn.close()

    def is_user_banned(self, user_id: int) -> bool:
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('SELECT is_banned FROM user_data WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        conn.close()
        return bool(result[0]) if result else False

    def log_message(self, chat_id: int, user_id: int, message_type: str, content: str):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('INSERT INTO chat_messages (chat_id, user_id, message_type, message_date, content) \
                  VALUES (?, ?, ?, ?, ?)',
                 (chat_id, user_id, message_type, datetime.now().isoformat(), content))
        conn.commit()
        conn.close()

    def get_user_stats(self, user_id: int) -> dict:
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('SELECT warnings, is_banned, join_date FROM user_data WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        stats = {
            'warnings': result[0] if result else 0,
            'is_banned': bool(result[1]) if result else False,
            'join_date': result[2] if result else None
        }
        conn.close()
        return stats

    # New methods for enhanced features
    def save_note(self, user_id: int, group_id: int, title: str, content: str, tags: list = None) -> int:
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        c.execute('''INSERT INTO notes (user_id, group_id, title, content, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                 (user_id, group_id, title, content, now, now))
        note_id = c.lastrowid
        
        if tags:
            for tag in tags:
                # Create or get tag
                c.execute('INSERT OR IGNORE INTO tags (name, group_id) VALUES (?, ?)',
                         (tag, group_id))
                c.execute('SELECT tag_id FROM tags WHERE name = ? AND group_id = ?',
                         (tag, group_id))
                tag_id = c.fetchone()[0]
                
                # Link note to tag
                c.execute('INSERT INTO note_tags (note_id, tag_id) VALUES (?, ?)',
                         (note_id, tag_id))
        
        conn.commit()
        conn.close()
        return note_id

    def get_notes(self, user_id: int, group_id: int = None) -> list:
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        if group_id:
            c.execute('''SELECT n.*, GROUP_CONCAT(t.name) as tags
                        FROM notes n
                        LEFT JOIN note_tags nt ON n.note_id = nt.note_id
                        LEFT JOIN tags t ON nt.tag_id = t.tag_id
                        WHERE n.user_id = ? AND n.group_id = ?
                        GROUP BY n.note_id''',
                     (user_id, group_id))
        else:
            c.execute('''SELECT n.*, GROUP_CONCAT(t.name) as tags
                        FROM notes n
                        LEFT JOIN note_tags nt ON n.note_id = nt.note_id
                        LEFT JOIN tags t ON nt.tag_id = t.tag_id
                        WHERE n.user_id = ?
                        GROUP BY n.note_id''',
                     (user_id,))
        
        notes = []
        for row in c.fetchall():
            note = {
                'note_id': row[0],
                'title': row[3],
                'content': row[4],
                'created_at': row[5],
                'updated_at': row[6],
                'tags': row[7].split(',') if row[7] else []
            }
            notes.append(note)
        
        conn.close()
        return notes

    def set_reminder(self, user_id: int, group_id: int, content: str, remind_at: str) -> int:
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        c.execute('''INSERT INTO reminders (user_id, group_id, content, remind_at, created_at)
                    VALUES (?, ?, ?, ?, ?)''',
                 (user_id, group_id, content, remind_at, now))
        reminder_id = c.lastrowid
        
        conn.commit()
        conn.close()
        return reminder_id

    def get_due_reminders(self) -> list:
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        c.execute('''SELECT * FROM reminders 
                    WHERE remind_at <= ? AND is_completed = 0''',
                 (now,))
        
        reminders = []
        for row in c.fetchall():
            reminder = {
                'reminder_id': row[0],
                'user_id': row[1],
                'group_id': row[2],
                'content': row[3],
                'remind_at': row[4],
                'created_at': row[5]
            }
            reminders.append(reminder)
        
        conn.close()
        return reminders

    def set_user_preference(self, user_id: int, preferences: dict):
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        c.execute('''INSERT OR REPLACE INTO user_preferences 
                    (user_id, theme, timezone, notification_preferences)
                    VALUES (?, ?, ?, ?)''',
                 (user_id,
                  preferences.get('theme', 'light'),
                  preferences.get('timezone', 'UTC'),
                  json.dumps(preferences.get('notifications', {}))))
        
        conn.commit()
        conn.close()

    def get_user_preference(self, user_id: int) -> dict:
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        c.execute('SELECT * FROM user_preferences WHERE user_id = ?', (user_id,))
        row = c.fetchone()
        
        if row:
            preferences = {
                'theme': row[1],
                'timezone': row[2],
                'notifications': json.loads(row[3]) if row[3] else {}
            }
        else:
            preferences = {
                'theme': 'light',
                'timezone': 'UTC',
                'notifications': {}
            }
        
        conn.close()
        return preferences

    def search_notes(self, user_id: int, query: str) -> list:
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        c.execute('''SELECT n.*, GROUP_CONCAT(t.name) as tags
                    FROM notes n
                    LEFT JOIN note_tags nt ON n.note_id = nt.note_id
                    LEFT JOIN tags t ON nt.tag_id = t.tag_id
                    WHERE n.user_id = ? AND (n.title LIKE ? OR n.content LIKE ?)
                    GROUP BY n.note_id''',
                 (user_id, f'%{query}%', f'%{query}%'))
        
        notes = []
        for row in c.fetchall():
            note = {
                'note_id': row[0],
                'title': row[3],
                'content': row[4],
                'created_at': row[5],
                'updated_at': row[6],
                'tags': row[7].split(',') if row[7] else []
            }
            notes.append(note)
        
        conn.close()
        return notes 