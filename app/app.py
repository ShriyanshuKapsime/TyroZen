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

@app.route("/todotest")
def todotest():
    return render_template("todotest.html")







# Register route

@app.route("/register", methods=["GET", "POST"])
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



# ------------------------------------------
#  TODO ROUTES
# ------------------------------------------
# ------------------------------------------
#  USER DATA STORAGE (todo, notes, habits, etc.)
# ------------------------------------------

USER_DATA_FOLDER = "./data/users/"

# Create folder if not exists
if not os.path.exists(USER_DATA_FOLDER):
    os.makedirs(USER_DATA_FOLDER)


def user_data_path(email):
    """Convert email into a safe filename."""
    safe = email.replace("@", "_").replace(".", "_")
    return os.path.join(USER_DATA_FOLDER, f"{safe}.json")


def load_user_data(email):
    """Load the user's individual data file. Create if missing."""
    path = user_data_path(email)

    if not os.path.exists(path):
        # default structure for each user
        data = {
            "todo": [],
            "notes": [],
            "habits": [],
            "budget": {},
            "attendance": {}
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
        return data

    with open(path, "r") as f:
        return json.load(f)


def save_user_data(email, data):
    """Save user's data back to their JSON file."""
    path = user_data_path(email)
    with open(path, "w") as f:
        json.dump(data, f, indent=4)



@app.route("/todo", methods=["GET", "POST"])
def todo():
    if "user" not in session:
        return redirect("/login")

    email = session["user"]["email"]
    data = load_user_data(email)

    # Ensure user's todo structure exists
    if "todo" not in data:
        data["todo"] = []

    if request.method == "POST":
        task = request.form["task"]
        category = request.form["category"]       # daily / weekly / monthly / yearly
        priority = request.form["priority"]       # low / medium / high
        deadline = request.form["deadline"]       # optional: date string

        new_task = {
            "task": task,
            "category": category,
            "priority": priority,
            "deadline": deadline,
            "completed": False
        }

        data["todo"].append(new_task)
        save_user_data(email, data)

        return redirect("/todo")

    return render_template("todo.html", todo=data["todo"])




@app.route("/todo/toggle/<int:index>")
def todo_toggle(index):
    if "user" not in session:
        return redirect("/login")

    email = session["user"]["email"]
    data = load_user_data(email)

    if 0 <= index < len(data["todo"]):
        data["todo"][index]["completed"] = not data["todo"][index]["completed"]
        save_user_data(email, data)

    return redirect("/todo")


@app.route("/todo/delete/<int:index>")
def todo_delete(index):
    if "user" not in session:
        return redirect("/login")

    email = session["user"]["email"]
    data = load_user_data(email)

    if 0 <= index < len(data["todo"]):
        data["todo"].pop(index)
        save_user_data(email, data)

    return redirect("/todo")


# ---------------- Notes Routes ----------------
@app.route("/notes", methods=["GET", "POST"])
def notes():
    if "user" not in session:
        return redirect("/login")

    email = session["user"]["email"]
    data = load_user_data(email)

    if "notes" not in data:
        data["notes"] = []

    # Add new note
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        tags = request.form.get("tags", "").split(",")  # comma-separated tags

        new_note = {
            "title": title,
            "content": content,
            "tags": [t.strip() for t in tags if t.strip()]
        }

        data["notes"].append(new_note)
        save_user_data(email, data)
        return redirect("/notes")

    # Search and tag filter
    search_query = request.args.get("search", "")
    filter_tag = request.args.get("tag", "")
    notes_list = data["notes"]

    if search_query:
        notes_list = [n for n in notes_list if search_query.lower() in n["title"].lower()]
    if filter_tag:
        notes_list = [n for n in notes_list if filter_tag in n.get("tags", [])]

    # Collect all tags for sidebar
    all_tags = sorted(set(tag for note in data["notes"] for tag in note.get("tags", [])))

    return render_template("notes.html", notes=notes_list, search_query=search_query, all_tags=all_tags)


@app.route("/notes/delete/<int:index>")
def notes_delete(index):
    if "user" not in session:
        return redirect("/login")

    email = session["user"]["email"]
    data = load_user_data(email)

    if 0 <= index < len(data["notes"]):
        data["notes"].pop(index)
        save_user_data(email, data)

    return redirect("/notes")


@app.route("/notes/edit/<int:index>", methods=["GET", "POST"])
def notes_edit(index):
    if "user" not in session:
        return redirect("/login")

    email = session["user"]["email"]
    data = load_user_data(email)

    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        tags = request.form.get("tags", "").split(",")
        data["notes"][index]["title"] = title
        data["notes"][index]["content"] = content
        data["notes"][index]["tags"] = [t.strip() for t in tags if t.strip()]
        save_user_data(email, data)
        return redirect("/notes")

    note = data["notes"][index]
    return render_template("notes_edit.html", note=note, index=index)





# ---------------- Attendance Routes ----------------
@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    if "user" not in session:
        return redirect("/login")

    email = session["user"]["email"]
    data = load_user_data(email)

    if "attendance" not in data:
        data["attendance"] = []

    # Add new subject
    if request.method == "POST":
        subject_name = request.form["subject"]
        total_classes = int(request.form["total_classes"])
        attended_classes = int(request.form["attended_classes"])
        min_percentage = 75  # you can make this configurable

        attendance_percentage = (attended_classes / total_classes) * 100 if total_classes > 0 else 0
        max_skips = int((attended_classes - total_classes * min_percentage / 100) * -1)
        if max_skips < 0:
            max_skips = 0

        new_subject = {
            "subject": subject_name,
            "total_classes": total_classes,
            "attended_classes": attended_classes,
            "attendance_percentage": round(attendance_percentage, 2),
            "max_skips": max_skips
        }

        data["attendance"].append(new_subject)
        save_user_data(email, data)
        return redirect("/attendance")

    return render_template("attendance.html", subjects=data["attendance"])


@app.route("/attendance/delete/<int:index>")
def attendance_delete(index):
    if "user" not in session:
        return redirect("/login")

    email = session["user"]["email"]
    data = load_user_data(email)

    if 0 <= index < len(data["attendance"]):
        data["attendance"].pop(index)
        save_user_data(email, data)

    return redirect("/attendance")


@app.route("/attendance/edit/<int:index>", methods=["GET", "POST"])
def attendance_edit(index):
    if "user" not in session:
        return redirect("/login")

    email = session["user"]["email"]
    data = load_user_data(email)

    if request.method == "POST":
        total_classes = int(request.form["total_classes"])
        attended_classes = int(request.form["attended_classes"])
        min_percentage = 75

        data["attendance"][index]["total_classes"] = total_classes
        data["attendance"][index]["attended_classes"] = attended_classes
        data["attendance"][index]["attendance_percentage"] = round((attended_classes / total_classes) * 100, 2)
        max_skips = int((attended_classes - total_classes * min_percentage / 100) * -1)
        if max_skips < 0:
            max_skips = 0
        data["attendance"][index]["max_skips"] = max_skips

        save_user_data(email, data)
        return redirect("/attendance")

    subject = data["attendance"][index]
    return render_template("attendance_edit.html", subject=subject, index=index)



if __name__ == "__main__":
    app.run(debug=True)
