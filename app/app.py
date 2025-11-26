from flask import Flask, render_template, request, redirect, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import json, os

app = Flask(__name__)
app.secret_key = "supersecretkey"

DATA_DIR = "data"
USER_DB = os.path.join(DATA_DIR, "users.json")

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def load_users():
    ensure_data_dir()
    if not os.path.exists(USER_DB):
        return []
    with open(USER_DB, "r") as f:
        try:
            return json.load(f)
        except:
            return []

def save_users(users):
    ensure_data_dir()
    with open(USER_DB, "w") as f:
        json.dump(users, f, indent=4)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/register", methods=["POST"])
def register():
    name = request.form["name"]
    email = request.form["email"].lower()
    password = request.form["password"]

    users = load_users()

    for u in users:
        if u["email"] == email:
            return jsonify({"success": False, "message": "User already exists!"})

    hashed_pwd = generate_password_hash(password)
    users.append({"name": name, "email": email, "password": hashed_pwd})
    save_users(users)

    return jsonify({"success": True, "message": "Account created! Please log in."})

@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"].lower()
    password = request.form["password"]

    users = load_users()

    for u in users:
        if u["email"] == email and check_password_hash(u["password"], password):
            session["user"] = {"name": u["name"], "email": email}
            return jsonify({"success": True, "redirect": "/dashboard"})

    return jsonify({"success": False, "message": "Invalid email or password"})

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    return render_template("dashboard.html", user=session["user"])

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
def get_user_file(email):
    """Returns the JSON file path for a specific user's stored data"""
    safe_email = email.replace("@", "_at_").replace(".", "_dot_")
    return os.path.join(DATA_DIR, f"{safe_email}.json")


def load_user_data(email):
    file = get_user_file(email)
    if not os.path.exists(file):
        default_data = {
            "todos": [],
            "notes": [],
            "habits": [],
            "attendance": {"attended": 0, "total": 0},
            "budget": {
                "total": 0,
                "remaining": 0,
                "expenses": []
            },
            "documents": []
        }
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(file, "w") as f:
            json.dump(default_data, f, indent=4)
        return default_data

    with open(file, "r") as f:
        return json.load(f)

def save_user_data(email, data):
    with open(get_user_file(email), "w") as f:
        json.dump(data, f, indent=4)

# attendance route

# budget route
@app.route("/budget", methods=["GET", "POST"])
def budget():
    if "user" not in session:
        return redirect("/login")

    email = session["user"]["email"]
    data = load_user_data(email)

    if isinstance(data.get("budget"), list):
        data["budget"] = {
            "total": 0,
            "remaining": 0,
            "expenses": []
        }
        save_user_data(email, data)

    budget_data = data["budget"]

    # -------- 1. SET MONTHLY BUDGET --------
    if request.form.get("form_type") == "set_budget":
        total = float(request.form["total"])
        budget_data["total"] = total
        budget_data["remaining"] = total
        budget_data["expenses"] = []   # clears expenses when budget resets
        save_user_data(email, data)
        return redirect("/budget")

    # -------- 2. ADD EXPENSE --------
    if request.form.get("form_type") == "add_expense":
        item = request.form["item"]
        amount = float(request.form["amount"])
        category = request.form["category"]

        budget_data["remaining"] -= amount

        budget_data["expenses"].append({
            "item": item,   
            "amount": amount,
            "category": category
        })

        save_user_data(email, data)
        return redirect("/budget")

    # -------- 3. CATEGORY BREAKDOWN --------
    category_totals = {}
    for e in budget_data["expenses"]:
        category_totals[e["category"]] = \
            category_totals.get(e["category"], 0) + e["amount"]

    return render_template(
        "budget.html",
        total=budget_data["total"],
        remaining=budget_data["remaining"],
        expenses=budget_data["expenses"],
        category_totals=category_totals
    )
# documents route 


# last block
if __name__ == "__main__":
    app.run(debug=True)
    
@app.route("/check-login")
def check_login():
    return jsonify({"logged_in": "user" in session})
