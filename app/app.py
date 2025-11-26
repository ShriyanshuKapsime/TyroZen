from flask import Flask, render_template, request, redirect, session, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

USER_DB = "./data/users.json"

def load_users():
    if not os.path.exists(USER_DB):
        return []
    with open(USER_DB, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USER_DB, "w") as f:
        json.dump(users, f, indent=4)


# Register route

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        name = request.form["name"]

        users = load_users()

        # Check if user exists
        for u in users:
            if u["email"] == email:
                flash("User already exists!")
                return redirect("/register")

        hashed_pwd = generate_password_hash(password)

        users.append({"name": name, "email": email, "password": hashed_pwd})
        save_users(users)

        flash("Registered successfully! Login now.")
        return redirect("/login")

    return render_template("register.html")


# Login route

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        users = load_users()

        for u in users:
            if u["email"] == email and check_password_hash(u["password"], password):
                session["user"] = {
                        "email": email,
                        "name": u["name"]
                        }
                return redirect("/dashboard")

        flash("Invalid credentials!")
        return redirect("/login")

    return render_template("login.html")


# dashboard route

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html", user=session["user"])


# logout route

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)

