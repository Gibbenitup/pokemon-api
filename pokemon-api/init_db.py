import sqlite3

conn = sqlite3.connect("pokemon_scraper.db")
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    store TEXT,
    url TEXT UNIQUE,
    last_alert_time TIMESTAMP,
    stock_status TEXT,
    price TEXT,
    image TEXT,
    variant TEXT,
    last_snapshot TEXT
)
''')

conn.commit()
conn.close()
