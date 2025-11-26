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


@app.route("/todotest")
def todotest():
    return render_template("todotest.html")







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







if __name__ == "__main__":
    app.run(debug=True)

