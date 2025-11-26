from flask import (
    Flask, render_template, request, redirect, session, url_for, flash,
    jsonify, send_from_directory
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import date
import json
import os
import google.generativeai as genai

GEMINI_API_KEY = "AIzaSyBNabw8DFSOEZwdAJ07YOLL5plfB_FDD5U"
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("models/gemini-2.5-flash")

def call_ai(prompt):
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI Error: {str(e)}"


# ------------------ CONFIG ------------------
app = Flask(__name__)
app.secret_key = "supersecretkey"  # change for production

USER_DATA_FOLDER = "./data/users/"
UPLOAD_FOLDER = "./uploads/"
ALLOWED = {"pdf", "png", "jpg", "jpeg"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


os.makedirs(USER_DATA_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
# --------------------------------------------

# ------------------ HELPERS -----------------
def safe_filename_from_email(email: str) -> str:
    """Create a safe filename from email."""
    return email.replace("@", "_at_").replace(".", "_dot_")

def user_data_path(email: str) -> str:
    safe = safe_filename_from_email(email)
    return os.path.join(USER_DATA_FOLDER, f"{safe}.json")

def load_user_data(email: str) -> dict:
    path = user_data_path(email)
    if not os.path.exists(path):
        default = {
            "todos": [],
            "notes": [],
            "habits": [],
            "attendance": {"attended": 0, "total": 0},
            "budget": {"total": 0, "remaining": 0, "expenses": []},
            "documents": []
        }
        with open(path, "w") as f:
            json.dump(default, f, indent=4)
        return default
    with open(path, "r") as f:
        return json.load(f)

def save_user_data(email: str, data: dict):
    path = user_data_path(email)
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def load_users() -> list:
    """Load global users list (users.json at project root)."""
    if not os.path.exists("users.json"):
        return []
    with open("users.json", "r") as f:
        try:
            return json.load(f)
        except:
            return []

def save_users(users: list):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED
# --------------------------------------------

# ------------------ ROUTES ------------------
@app.route("/")
def index():
    # If logged in, send to dashboard; else show landing/login page
    if "user" in session:
        return redirect("/dashboard")
    return render_template("index.html")  # you should have index.html

# --------- JSON register (Option A) ----------
@app.route("/register", methods=["POST"])
def register():
    # Expect JSON or form data with fields: name, email, password
    name = request.form.get("name") or request.json.get("name")
    email = (request.form.get("email") or request.json.get("email") or "").lower().strip()
    password = request.form.get("password") or request.json.get("password")

    if not name or not email or not password:
        return jsonify({"success": False, "message": "Missing fields"}), 400

    users = load_users()
    if any(u["email"] == email for u in users):
        return jsonify({"success": False, "message": "User already exists"}), 400

    hashed = generate_password_hash(password)
    users.append({"name": name, "email": email, "password": hashed})
    save_users(users)

    # create empty user data file
    load_user_data(email)

    return jsonify({"success": True, "message": "Registered successfully"})

# --------- JSON login (Option A) --------------
@app.route("/login", methods=["POST"])
def login():
    email = (request.form.get("email") or request.json.get("email") or "").lower().strip()
    password = request.form.get("password") or request.json.get("password")

    if not email or not password:
        return jsonify({"success": False, "message": "Missing credentials"}), 400

    users = load_users()
    for u in users:
        if u["email"] == email and check_password_hash(u["password"], password):
            # set session
            session["user"] = {"email": email, "name": u.get("name", "")}
            return jsonify({"success": True, "redirect": "/dashboard"})
    return jsonify({"success": False, "message": "Invalid email or password"}), 401

# --------- Dashboard (HTML) -------------------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/")
    user = session["user"]
    data = load_user_data(user["email"])
    # Prepare a small summary for the dashboard template
    summary = {
        "todos_count": len(data.get("todos", [])),
        "notes_count": len(data.get("notes", [])),
        "habits_count": len(data.get("habits", [])),
        "attendance": data.get("attendance", {"attended": 0, "total": 0}),
        "budget": data.get("budget", {"total": 0, "remaining": 0}),
        "documents_count": len(data.get("documents", []))
    }
    return render_template("dashboard.html", user=user, summary=summary)

# --------- Logout -----------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
def get_user_file(email):
    """Returns the JSON file path for a specific user's stored data"""
    safe_email = email.replace("@", "_at_").replace(".", "_dot_")
    return os.path.join(DATA_DIR, f"{safe_email}.json")


from flask import Flask, render_template, request, redirect, session

# --------- Attendance --------------------------
def calculate_max_skips(total_classes, attended_classes, classes_done):
    """
    Calculates max classes user can skip in the remaining classes
    while still maintaining 75% overall attendance.
    """
    if total_classes <= 0:
        return 0

    # Minimum number of classes that must be attended to maintain 75%
    min_attendance_needed = int(0.85 * total_classes + 0.999)  # round up

    # Classes left to be conducted
    remaining_classes = total_classes - classes_done

    # Classes still required to reach minimum attendance
    required_attendance_remaining = max(min_attendance_needed - attended_classes, 0)

    # Max skips = remaining classes - required attendance remaining
    max_skips = remaining_classes - required_attendance_remaining

    return max(max_skips, 0)


@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    if "user" not in session:
        return redirect("/login")
    email = session["user"]["email"]
    data = load_user_data(email)

    if "attendance" not in data:
        data["attendance"] = []

    if request.method == "POST":
        subject_name = request.form["subject"]
        total_classes = int(request.form["total_classes"])
        classes_done = int(request.form["classes_done"])
        attended_classes = int(request.form["attended_classes"])

        # Validate numbers
        if not (0 <= attended_classes <= classes_done <= total_classes):
            flash("Invalid attendance values!", "error")
            return redirect("/attendance")

        attendance_percentage = round((attended_classes / classes_done) * 100, 2) if classes_done > 0 else 0
        max_skips = calculate_max_skips(total_classes, attended_classes, classes_done)

        new_subject = {
            "subject": subject_name,
            "total_classes": total_classes,
            "classes_done": classes_done,
            "attended_classes": attended_classes,
            "attendance_percentage": attendance_percentage,
            "max_skips": max_skips
        }

        data["attendance"].append(new_subject)
        save_user_data(email, data)
        return redirect("/attendance")

    return render_template("attendance.html", subjects=data["attendance"])


@app.route("/attendance/delete/<int:index>", methods=["POST"])
def attendance_delete(index):
    if "user" not in session:
        return redirect("/login")
    email = session["user"]["email"]
    data = load_user_data(email)

    if 0 <= index < len(data.get("attendance", [])):
        data["attendance"].pop(index)
        save_user_data(email, data)

    return redirect("/attendance")


@app.route("/attendance/edit/<int:index>", methods=["GET", "POST"])
def attendance_edit(index):
    if "user" not in session:
        return redirect("/login")
    email = session["user"]["email"]
    data = load_user_data(email)

    if not (0 <= index < len(data.get("attendance", []))):
        flash("Invalid index!", "error")
        return redirect("/attendance")

    subject = data["attendance"][index]

    if request.method == "POST":
        total_classes = int(request.form["total_classes"])
        classes_done = int(request.form["classes_done"])
        attended_classes = int(request.form["attended_classes"])

        # Validate numbers
        if not (0 <= attended_classes <= classes_done <= total_classes):
            flash("Invalid attendance values!", "error")
            return redirect(f"/attendance/edit/{index}")

        attendance_percentage = round((attended_classes / classes_done) * 100, 2) if classes_done > 0 else 0
        max_skips = calculate_max_skips(total_classes, attended_classes, classes_done)

        subject.update({
            "total_classes": total_classes,
            "classes_done": classes_done,
            "attended_classes": attended_classes,
            "attendance_percentage": attendance_percentage,
            "max_skips": max_skips
        })

        save_user_data(email, data)
        return redirect("/attendance")

    return render_template("attendance_edit.html", subject=subject, index=index)

# --------- Budget (single route) --------------
@app.route("/budget", methods=["GET", "POST"])
def budget():
    if "user" not in session:
        return redirect("/")
    email = session["user"]["email"]
    data = load_user_data(email)

    # ensure structured budget
    if isinstance(data.get("budget"), list) or data.get("budget") is None:
        data["budget"] = {"total": 0, "remaining": 0, "expenses": []}

    budget_data = data["budget"]
    ai_advice = None   # NEW — default AI response is empty

    # ---------------- SET BUDGET ----------------
    if request.form.get("form_type") == "set_budget":
        try:
            total = float(request.form.get("total", 0))
        except ValueError:
            flash("Invalid amount", "error")
            return redirect("/budget")
        budget_data["total"] = total
        budget_data["remaining"] = total
        budget_data["expenses"] = []
        save_user_data(email, data)
        return redirect("/budget")

    # ---------------- ADD EXPENSE ----------------
    if request.form.get("form_type") == "add_expense":
        item = request.form.get("item", "").strip()
        try:
            amount = float(request.form.get("amount", 0))
        except ValueError:
            flash("Invalid amount", "error")
            return redirect("/budget")
        category = request.form.get("category", "Other")
        budget_data["remaining"] = round(budget_data.get("remaining", 0) - amount, 2)
        budget_data["expenses"].append({"item": item, "amount": amount, "category": category})
        save_user_data(email, data)
        return redirect("/budget")

    # ---------------- AI ADVICE ----------------
    if request.form.get("form_type") == "ai_advice":
        prompt = f"""
        You are an AI financial advisor for college students.
        Analyze this budget:

        Total Budget: {budget_data.get('total')}
        Remaining: {budget_data.get('remaining')}
        Expenses: {budget_data.get('expenses')}

        Give clear, simple, actionable advice in 4–6 sentences.
        """
        ai_advice = call_ai(prompt)

    # ---------------- CATEGORY TOTALS ----------------
    category_totals = {}
    for e in budget_data.get("expenses", []):
        category_totals[e["category"]] = category_totals.get(e["category"], 0) + e["amount"]

    return render_template(
        "budget.html",
        total=budget_data.get("total", 0),
        remaining=budget_data.get("remaining", 0),
        expenses=budget_data.get("expenses", []),
        category_totals=category_totals,
        ai_advice=ai_advice     # NEW — pass AI text to page
    )


# --------- Habit Tracker -----------------------
# ------------------ Habit Tracker ------------------
@app.route("/habits", methods=["GET", "POST"])
def habits():
    if "user" not in session:
        return redirect("/login")  # or "/" depending on your app
    email = session["user"]["email"]
    data = load_user_data(email)

    # Add new habit
    if request.method == "POST" and request.form.get("form_type") == "add_habit":
        name = request.form.get("habit_name", "").strip()
        if name:
            data.setdefault("habits", []).append({
                "name": name,
                "streak": 0,
                "last_done": None
            })
            save_user_data(email, data)
        return redirect("/habits")

    return render_template("habits.html", habits=data.get("habits", []))


@app.route("/habit/done/<int:index>")
def habit_done(index):
    if "user" not in session:
        return redirect("/login")
    email = session["user"]["email"]
    data = load_user_data(email)
    habits = data.get("habits", [])

    if 0 <= index < len(habits):
        habit = habits[index]
        today = date.today()
        last = None
        if habit.get("last_done"):
            try:
                last = date.fromisoformat(habit["last_done"])
            except:
                last = None

        # Already done today?
        if habit.get("last_done") == str(today):
            return redirect("/habits")

        # Increment streak if yesterday done, else reset
        if last and (today.toordinal() - last.toordinal() == 1):
            habit["streak"] = habit.get("streak", 0) + 1
        else:
            habit["streak"] = 1

        habit["last_done"] = str(today)
        save_user_data(email, data)

    return redirect("/habits")


@app.route("/habit/delete/<int:index>")
def habit_delete(index):
    if "user" not in session:
        return redirect("/login")
    email = session["user"]["email"]
    data = load_user_data(email)

    if 0 <= index < len(data.get("habits", [])):
        data["habits"].pop(index)
        save_user_data(email, data)

    return redirect("/habits")

# --------- Todo -------------------------------
@app.route("/todo", methods=["GET", "POST"])
def todo():
    if "user" not in session:
        return redirect("/")
    email = session["user"]["email"]
    data = load_user_data(email)
    data.setdefault("todos", [])

    if request.method == "POST":
        task = request.form.get("task", "").strip()
        category = request.form.get("category", "").strip()
        priority = request.form.get("priority", "").strip()
        deadline = request.form.get("deadline", "").strip()
        if task:
            data["todos"].append({
                "task": task, "category": category, "priority": priority, "deadline": deadline, "completed": False
            })
            save_user_data(email, data)
        return redirect("/todo")

    return render_template("todo.html", todo=data.get("todos", []))

@app.route("/todo/toggle/<int:index>")
def todo_toggle(index):
    if "user" not in session:
        return redirect("/")
    email = session["user"]["email"]
    data = load_user_data(email)
    if 0 <= index < len(data.get("todos", [])):
        data["todos"][index]["completed"] = not data["todos"][index].get("completed", False)
        save_user_data(email, data)
    return redirect("/todo")

@app.route("/todo/delete/<int:index>")
def todo_delete(index):
    if "user" not in session:
        return redirect("/")
    email = session["user"]["email"]
    data = load_user_data(email)
    if 0 <= index < len(data.get("todos", [])):
        data["todos"].pop(index)
        save_user_data(email, data)
    return redirect("/todo")

# --------- Notes --------------------------------
@app.route("/notes", methods=["GET", "POST"])
def notes():
    if "user" not in session:
        return redirect("/")
    email = session["user"]["email"]
    data = load_user_data(email)
    data.setdefault("notes", [])

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        tags = [t.strip() for t in (request.form.get("tags", "") or "").split(",") if t.strip()]
        if title or content:
            data["notes"].append({"title": title, "content": content, "tags": tags})
            save_user_data(email, data)
        return redirect("/notes")

    # filters
    search_query = request.args.get("search", "").strip()
    filter_tag = request.args.get("tag", "").strip()
    notes_list = data.get("notes", [])
    if search_query:
        notes_list = [n for n in notes_list if search_query.lower() in n.get("title", "").lower()]
    if filter_tag:
        notes_list = [n for n in notes_list if filter_tag in n.get("tags", [])]
    all_tags = sorted({t for n in data.get("notes", []) for t in n.get("tags", [])})
    return render_template("notes.html", notes=notes_list, search_query=search_query, all_tags=all_tags)

@app.route("/notes/delete/<int:index>")
def notes_delete(index):
    if "user" not in session:
        return redirect("/")
    email = session["user"]["email"]
    data = load_user_data(email)
    if 0 <= index < len(data.get("notes", [])):
        data["notes"].pop(index)
        save_user_data(email, data)
    return redirect("/notes")

@app.route("/notes/edit/<int:index>", methods=["GET", "POST"])
def notes_edit(index):
    if "user" not in session:
        return redirect("/")
    email = session["user"]["email"]
    data = load_user_data(email)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        tags = [t.strip() for t in (request.form.get("tags", "") or "").split(",") if t.strip()]
        if 0 <= index < len(data.get("notes", [])):
            data["notes"][index].update({"title": title, "content": content, "tags": tags})
            save_user_data(email, data)
        return redirect("/notes")
    if 0 <= index < len(data.get("notes", [])):
        note = data["notes"][index]
        return render_template("notes_edit.html", note=note, index=index)
    return redirect("/notes")

# --------- Documents upload & view -------------
@app.route("/uploads/<path:filename>")
def uploaded_files(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/documents", methods=["GET", "POST"])
def documents():
    if "user" not in session:
        return redirect("/")
    email = session["user"]["email"]
    data = load_user_data(email)

    user_folder = os.path.join(UPLOAD_FOLDER, safe_filename_from_email(email))
    os.makedirs(user_folder, exist_ok=True)

    if request.method == "POST":
        category = request.form.get("category", "Others")
        file = request.files.get("file")
        if not file or file.filename == "":
            flash("No file selected.", "error")
            return redirect("/documents")
        if not allowed_file(str(file.filename)):
            flash("File type not allowed.", "error")
            return redirect("/documents")
        filename = secure_filename(str(file.filename))
        save_path = os.path.join(user_folder, filename)
        file.save(save_path)
        # store path relative to uploads root: safe_email/filename
        data.setdefault("documents", []).append({"name": filename, "path": f"{safe_filename_from_email(email)}/{filename}", "category": category})
        save_user_data(email, data)
        return redirect("/documents")

    # group docs by category for display
    docs_by_category = {"Notes": [], "Assignments": [], "Modules": [], "Others": []}
    for d in data.get("documents", []):
        cat = d.get("category", "Others")
        docs_by_category.setdefault(cat, []).append(d)
    return render_template("documents.html", docs_by_category=docs_by_category)

@app.route("/check-login")
def check_login():
    return jsonify({"logged_in": "user" in session})

@app.route("/delete_document/<path:path>")
def delete_document(path):
    if "user" not in session:
        return redirect("/")

    email = session["user"]["email"]
    data = load_user_data(email)

    # 1. Delete file from disk
    full_path = os.path.join(UPLOAD_FOLDER, path)
    if os.path.exists(full_path):
        os.remove(full_path)

    # 2. Remove entry from user's JSON
    data["documents"] = [d for d in data.get("documents", []) if d["path"] != path]
    save_user_data(email, data)

    # 3. Redirect back
    return redirect(url_for("documents"))



# ai budget
@app.route("/ai/budget")
def ai_budget():
    if "user" not in session:
        return redirect("/")

    email = session["user"]["email"]
    data = load_user_data(email)

    budget = data["budget"]
    prompt = f"""
    You are an AI financial advisor for college students.

    Analyze the user's budget:

    Total Budget: {budget.get('total')}
    Remaining: {budget.get('remaining')}
    Expenses: {budget.get('expenses')}

    Give clear, simple, actionable advice in 4–6 sentences.
    """

    advice = call_ai(prompt)

    return render_template("ai_budget.html", advice=advice, budget=budget)


# -----------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
    



