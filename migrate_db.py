from utils import db
print("Running migration...")
db.add_missing_columns()
print("Migration complete.")
