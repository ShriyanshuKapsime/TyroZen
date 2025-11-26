from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask import send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
import json
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = "./uploads/"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED = {"pdf", "png", "jpg", "jpeg"}
USER_DB = "users.json"
DATA_DIR = "./data/"

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

# user data helper 
def get_user_file(email):
    return os.path.join(DATA_DIR, f"{email}.json")

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

    # monthly budget
    if request.form.get("form_type") == "set_budget":
        total = float(request.form["total"])
        budget_data["total"] = total
        budget_data["remaining"] = total
        budget_data["expenses"] = []   # clears expenses when budget resets
        save_user_data(email, data)
        return redirect("/budget")

    # add expense
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

    # category breakdown
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

# Habit tracker
@app.route("/habits", methods=["GET", "POST"])
def habits():
    if "user" not in session:
        return redirect("/login")

    email = session["user"]["email"]
    data = load_user_data(email)

    # ----- Add New Habit -----
    if request.method == "POST" and request.form.get("form_type") == "add_habit":
        habit_name = request.form["habit_name"]
        data["habits"].append({
            "name": habit_name,
            "streak": 0,
            "last_done": None
        })
        save_user_data(email, data)
        return redirect("/habits")

    return render_template("habits.html", habits=data["habits"])


@app.route("/habit/done/<int:index>")
def habit_done(index):
    if "user" not in session:
        return redirect("/login")

    email = session["user"]["email"]
    data = load_user_data(email)

    today = str(date.today())
    habit = data["habits"][index]

    # If user already completed it today → do nothing
    if habit["last_done"] == today:
        return redirect("/habits")

    # If completed yesterday → streak +=1
    if habit["last_done"] == str(date.fromordinal(date.today().toordinal() - 1)):
        habit["streak"] += 1
    else:
        # Missed → streak resets
        habit["streak"] = 1

    habit["last_done"] = today

    save_user_data(email, data)
    return redirect("/habits")


@app.route("/habit/delete/<int:index>")
def delete_habit(index):
    if "user" not in session:
        return redirect("/login")

    email = session["user"]["email"]
    data = load_user_data(email)

    data["habits"].pop(index)
    save_user_data(email, data)

    return redirect("/habits")

# documents upload 2nd route
@app.route("/uploads/<path:filename>")
def uploaded_files(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# documents uploads
from werkzeug.utils import secure_filename

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED

# ---------------- DOCUMENT UPLOAD ----------------

@app.route("/documents", methods=["GET", "POST"])
def documents():
    if "user" not in session:
        return redirect("/login")

    email = session["user"]["email"]
    data = load_user_data(email)

    user_folder = os.path.join(UPLOAD_FOLDER, email)
    os.makedirs(user_folder, exist_ok=True)

    # ----- UPLOAD -----
    if request.method == "POST":
        category = request.form.get("category", "Others")
        file = request.files.get("file")

        if not file or file.filename == "":
            flash("No file selected.")
            return redirect("/documents")

        if not allowed_file(file.filename):
            flash("File type not allowed.")
            return redirect("/documents")

        filename = secure_filename(str(file.filename))
        save_path = os.path.join(user_folder, filename)
        file.save(save_path)

        data["documents"].append({
            "name": filename,
            "path": f"{email}/{filename}",
            "category": category
        })

        save_user_data(email, data)
        return redirect("/documents")

    # ----- CATEGORY GROUPING -----
    docs_by_category = {
        "Notes": [],
        "Assignments": [],
        "Modules": [],
        "Others": []
    }

    for d in data["documents"]:
        cat = d.get("category", "Others")
        docs_by_category.setdefault(cat, []).append(d)

    return render_template(
        "documents.html",
        docs_by_category=docs_by_category
    )



# last block
if __name__ == "__main__":
    app.run(debug=True)

