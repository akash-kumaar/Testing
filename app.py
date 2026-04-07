from flask import Flask, request, jsonify, render_template
import sqlite3
import datetime
import os

app = Flask(__name__)
# Vercel functions are read-only except for /tmp. 
# Data will reset over time unless an external DB (like Postgres) is used.
DB_FILE = "/tmp/expenses.db" if os.environ.get("VERCEL_URL") or os.environ.get("VERCEL") else "expenses.db"

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT,
                timestamp TEXT NOT NULL,
                is_essential BOOLEAN NOT NULL
            )
        ''')
        conn.commit()

init_db()

def categorize_expense(name, category):
    name_lower = name.lower()
    cat_lower = (category or "").lower()
    
    essential_keywords = ["rent", "groceries"]
    non_essential_keywords = ["netflix", "gaming", "starbucks", "games"]
    
    for kw in essential_keywords:
        if kw in name_lower or kw in cat_lower:
            return True
            
    for kw in non_essential_keywords:
        if kw in name_lower or kw in cat_lower:
            return False
            
    # Default behavior if not clear
    return True 

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/add_expense", methods=["POST"])
def add_expense():
    data = request.json
    name = data.get("name", "Unknown")
    amount = float(data.get("amount", 0.0))
    category = data.get("category", "")
    
    is_essential = categorize_expense(name, category)
    timestamp = datetime.datetime.now().isoformat()
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO expenses (name, amount, category, timestamp, is_essential)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, amount, category, timestamp, is_essential))
        conn.commit()
        expense_id = cursor.lastrowid
        
    return jsonify({
        "id": expense_id,
        "name": name,
        "amount": amount,
        "category": category,
        "timestamp": timestamp,
        "is_essential": is_essential
    }), 201

@app.route("/get_expenses", methods=["GET"])
def get_expenses():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, amount, category, timestamp, is_essential FROM expenses")
        rows = cursor.fetchall()
        
    expenses = []
    for row in rows:
        expenses.append({
            "id": row[0],
            "name": row[1],
            "amount": row[2],
            "category": row[3],
            "timestamp": row[4],
            "is_essential": bool(row[5])
        })
        
    return jsonify(expenses)

@app.route("/delete_expense/<int:expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        conn.commit()
    return jsonify({"success": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
