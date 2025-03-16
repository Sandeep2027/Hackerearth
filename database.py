import sqlite3
import csv
from datetime import datetime
import os

def init_db():
    conn = sqlite3.connect('defi_content.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    experience_level TEXT,
                    interests TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS content (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    title TEXT,
                    body TEXT,
                    topic TEXT,
                    category TEXT DEFAULT 'General',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_id INTEGER,
                    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                    comment TEXT,
                    sentiment REAL,
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (content_id) REFERENCES content(id))''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    content_id INTEGER,
                    interaction_type TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (content_id) REFERENCES content(id))''')
    conn.commit()
    conn.close()

def add_user(username, experience_level, interests):
    conn = sqlite3.connect('defi_content.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (username, experience_level, interests) VALUES (?, ?, ?)",
              (username, experience_level, interests))
    conn.commit()
    conn.close()

def get_user(username):
    conn = sqlite3.connect('defi_content.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = c.fetchone()
    conn.close()
    return user

def save_content(user_id, title, body, topic, category='General'):
    conn = sqlite3.connect('defi_content.db')
    c = conn.cursor()
    c.execute("INSERT INTO content (user_id, title, body, topic, category) VALUES (?, ?, ?, ?, ?)",
              (user_id, title, body, topic, category))
    conn.commit()
    conn.close()

def get_content_by_user(user_id, limit=10):
    conn = sqlite3.connect('defi_content.db')
    c = conn.cursor()
    c.execute("SELECT * FROM content WHERE user_id = ? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
    content = c.fetchall()
    conn.close()
    return content

def get_content_by_topic(topic, limit=5):
    conn = sqlite3.connect('defi_content.db')
    c = conn.cursor()
    c.execute("SELECT * FROM content WHERE topic LIKE ? ORDER BY created_at DESC LIMIT ?", (f"%{topic}%", limit))
    content = c.fetchall()
    conn.close()
    return content

def save_feedback(content_id, rating, comment, sentiment):
    conn = sqlite3.connect('defi_content.db')
    c = conn.cursor()
    c.execute("INSERT INTO feedback (content_id, rating, comment, sentiment) VALUES (?, ?, ?, ?)",
              (content_id, rating, comment, sentiment))
    conn.commit()
    conn.close()

def get_feedback_stats(content_id):
    conn = sqlite3.connect('defi_content.db')
    c = conn.cursor()
    c.execute("SELECT AVG(rating), COUNT(*), AVG(sentiment) FROM feedback WHERE content_id = ?", (content_id,))
    stats = c.fetchone()
    conn.close()
    return {"avg_rating": stats[0] if stats[0] is not None else 0,
            "total_reviews": stats[1],
            "avg_sentiment": stats[2] if stats[2] is not None else 0}

def log_interaction(user_id, content_id, interaction_type):
    conn = sqlite3.connect('defi_content.db')
    c = conn.cursor()
    c.execute("INSERT INTO user_interactions (user_id, content_id, interaction_type) VALUES (?, ?, ?)",
              (user_id, content_id, interaction_type))
    conn.commit()
    conn.close()

def get_user_recommendations(user_id):
    conn = sqlite3.connect('defi_content.db')
    c = conn.cursor()
    c.execute("""
        SELECT c.topic, COUNT(*) as freq
        FROM user_interactions ui
        JOIN content c ON ui.content_id = c.id
        WHERE ui.user_id = ?
        GROUP BY c.topic
        ORDER BY freq DESC
        LIMIT 3
    """, (user_id,))
    topics = c.fetchall()
    conn.close()
    return [t[0] for t in topics]

def get_user_analytics(user_id):
    conn = sqlite3.connect('defi_content.db')
    c = conn.cursor()
    c.execute("""
        SELECT COUNT(c.id), GROUP_CONCAT(DISTINCT c.topic), COUNT(f.id), AVG(f.rating)
        FROM users u
        LEFT JOIN content c ON u.id = c.user_id
        LEFT JOIN feedback f ON c.id = f.content_id
        WHERE u.id = ?
    """, (user_id,))
    analytics = c.fetchone()
    conn.close()
    return {"content_count": analytics[0],
            "topics": analytics[1],
            "feedback_count": analytics[2],
            "avg_rating": analytics[3] if analytics[3] is not None else 0}

def categorize_content(user_id):
    conn = sqlite3.connect('defi_content.db')
    c = conn.cursor()
    c.execute("SELECT category, COUNT(*) FROM content WHERE user_id = ? GROUP BY category", (user_id,))
    categories = c.fetchall()
    conn.close()
    return dict(categories)

def export_content_to_csv(user_id):
    conn = sqlite3.connect('defi_content.db')
    c = conn.cursor()
    c.execute("SELECT title, body, topic, category, created_at FROM content WHERE user_id = ?", (user_id,))
    content = c.fetchall()
    conn.close()
    
    os.makedirs('exports', exist_ok=True)
    file_path = f"exports/user_{user_id}_content.csv"
    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Title', 'Body', 'Topic', 'Category', 'Created At'])
        writer.writerows(content)
    return file_path