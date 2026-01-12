import pandas as pd
import os
from datetime import datetime
import streamlit as st

LOG_FILE = 'activity_log.csv'

def init_log_file():
    if not os.path.exists(LOG_FILE):
        df = pd.DataFrame(columns=['user_id', 'date', 'activity', 'duration_mins', 'notes'])
        df.to_csv(LOG_FILE, index=False)

def log_activity(user_id, activity_type, duration, notes=""):
    init_log_file()
    new_entry = {
        'user_id': user_id,
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'activity': activity_type,
        'duration_mins': duration,
        'notes': notes
    }
    df = pd.read_csv(LOG_FILE)
    df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    df.to_csv(LOG_FILE, index=False)

def get_user_history(user_id):
    init_log_file()
    df = pd.read_csv(LOG_FILE)
    if 'user_id' in df.columns:
        return df[df['user_id'] == user_id].sort_values(by='date', ascending=False)
    return pd.DataFrame()

def get_weekly_stats(user_id):
    df = get_user_history(user_id)
    # Simple aggregation logic could go here
    return df
