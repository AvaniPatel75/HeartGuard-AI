import sqlite3
import os
import json
import datetime

DB_NAME = 'heartguard.db'

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Users Table with Profile Info
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            full_name TEXT,
            phone TEXT,
            dob TEXT,
            address TEXT,
            blood_type TEXT,
            allergies TEXT,
            chronic_diseases TEXT,
            profile_pic TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Predictions Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            input_data TEXT NOT NULL, -- JSON string
            result TEXT NOT NULL,     -- JSON string
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES users (username)
        )
    ''')
    
    # Activity Logs Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            activity TEXT NOT NULL,
            duration INTEGER,
            date TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (username) REFERENCES users (username)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized.")

def migrate_from_files():
    """Attempt to migrate existing JSON/CSV data to SQLite"""
    if not os.path.exists(DB_NAME):
        init_db()
        
    conn = get_db_connection()
    c = conn.cursor()
    
    # Migrate Users
    if os.path.exists('users.json'):
        try:
            with open('users.json', 'r') as f:
                users = json.load(f)
            for username, data in users.items():
                # Check format (legacy str vs new dict)
                if isinstance(data, str):
                    password = data
                    role = 'admin' if username == 'admin' else 'user'
                else:
                    password = data.get('password')
                    role = data.get('role', 'user')
                
                try:
                    c.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)", 
                              (username, password, role))
                except: pass
            print("Users migrated.")
        except Exception as e: print(f"User migration failed: {e}")

    # Migrate Predictions
    if os.path.exists('predictions.json'):
        try:
            with open('predictions.json', 'r') as f:
                preds = json.load(f)
            for p in preds:
                try:
                    c.execute("INSERT INTO predictions (username, input_data, result, timestamp) VALUES (?, ?, ?, ?)",
                              (p['user'], json.dumps(p['input']), json.dumps(p['result']), p['timestamp']))
                except: pass
            print("Predictions migrated.")
        except Exception as e: print(f"Prediction migration failed: {e}")

    # Migrate Activity Logs
    if os.path.exists('activity_log.csv'):
        try:
            import pandas as pd
            df = pd.read_csv('activity_log.csv')
            for _, row in df.iterrows():
                try:
                    c.execute("INSERT INTO activity_logs (username, activity, duration, date) VALUES (?, ?, ?, ?)",
                              (row['user'], row['activity'], row['duration'], row['date']))
                except: pass
            print("Activity logs migrated.")
        except Exception as e: print(f"Activity migration failed: {e}")
        
    conn.commit()
    conn.close()

# Helper Functions for App

def add_user(username, password, email=None, role='user'):
    conn = get_db_connection()
    try:
        conn.execute("INSERT INTO users (username, password, email, role) VALUES (?, ?, ?, ?)", (username, password, email, role))
        conn.commit()
        return True
    except Exception as e:
        print(f"Registration Error: {e}")
        return False
    finally:
        conn.close()

def get_user(username):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return user

def log_prediction(username, input_data, result):
    conn = get_db_connection()
    conn.execute("INSERT INTO predictions (username, input_data, result) VALUES (?, ?, ?)",
                 (username, json.dumps(input_data), json.dumps(result)))
    conn.commit()
    conn.close()

def log_activity(username, activity, duration, date):
    conn = get_db_connection()
    conn.execute("INSERT INTO activity_logs (username, activity, duration, date) VALUES (?, ?, ?, ?)",
                 (username, activity, duration, date))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return users

def get_all_predictions():
    conn = get_db_connection()
    preds = conn.execute("SELECT * FROM predictions ORDER BY timestamp DESC").fetchall()
    conn.close()
    return preds

def get_all_activity_logs():
    conn = get_db_connection()
    logs = conn.execute("SELECT * FROM activity_logs ORDER BY timestamp DESC").fetchall()
    conn.close()
    return logs

def get_user_history(username):
    conn = get_db_connection()
    # Removed LIMIT 5 to show all history in profile
    preds = conn.execute("SELECT * FROM predictions WHERE username = ? ORDER BY timestamp DESC", (username,)).fetchall()
    conn.close()
    return preds
    
def get_user_activity(username):
    conn = get_db_connection()
    logs = conn.execute("SELECT * FROM activity_logs WHERE username = ? ORDER BY timestamp DESC", (username,)).fetchall()
    conn.close()
    return logs

def get_all_user_predictions(username):
    conn = get_db_connection()
    preds = conn.execute("SELECT * FROM predictions WHERE username = ? ORDER BY timestamp DESC", (username,)).fetchall()
    conn.close()
    return preds

# --- User Profile Helpers ---
def update_user_profile(username, data):
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE users 
            SET full_name = ?, phone = ?, dob = ?, address = ?, blood_type = ?, allergies = ?, chronic_diseases = ?
            WHERE username = ?
        ''', (data.get('full_name'), data.get('phone'), data.get('dob'), data.get('address'), 
              data.get('blood_type'), data.get('allergies'), data.get('chronic_diseases'), username))
        conn.commit()
    except Exception as e:
        print(f"Error updating profile: {e}")
    finally:
        conn.close()

def get_user_details(username):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    return user

def update_password(email, new_password):
    conn = get_db_connection()
    try:
        conn.execute("UPDATE users SET password = ? WHERE email = ?", (new_password, email))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating password: {e}")
        return False
    finally:
        conn.close()

def add_missing_columns():
    """Safety migration for existing databases"""
    conn = get_db_connection()
    c = conn.cursor()
    columns = [
        ('full_name', 'TEXT'),
        ('phone', 'TEXT'),
        ('dob', 'TEXT'),
        ('address', 'TEXT'),
        ('blood_type', 'TEXT'),
        ('allergies', 'TEXT'),
        ('chronic_diseases', 'TEXT'),
        ('profile_pic', 'TEXT'),
        ('email', 'TEXT')
    ]
    for col, type_ in columns:
        try:
            c.execute(f'ALTER TABLE users ADD COLUMN {col} {type_}')
            print(f"Added column {col}")
        except sqlite3.OperationalError:
            pass # Column likely exists
    conn.commit()
    conn.close()
