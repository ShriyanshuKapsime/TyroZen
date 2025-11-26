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

if __name__ == "__main__":
    app.run(debug=True)
