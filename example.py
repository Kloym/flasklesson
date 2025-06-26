import os
import psycopg2
from flask import (
    get_flashed_messages,
    flash,
    Flask,
    redirect,
    render_template,
    request,
    url_for,
)
from user_repository import UserRepository

from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
app.config["DATABASE_URL"] = os.getenv("DATABASE_URL")

def get_repo():
    conn = psycopg2.connect(app.config["DATABASE_URL"])
    return UserRepository(conn), conn

@app.route("/")
def index():
    return render_template("home.html")


@app.route("/users/")
def users_get():
    repo, conn = get_repo()
    try:
        messages = get_flashed_messages(with_categories=True)
        term = request.args.get("term", "")
        if term:
            users = repo.get_by_term(term)
        else:
            users = repo.get_content()
        return render_template(
            "users/index.html", users=users, search=term, messages=messages
        )
    finally:
        conn.close()


@app.post("/users")
def users_post():
    conn, repo = get_repo()
    user_data = request.form.to_dict()
    errors = validate(user_data)
    if errors:
        return render_template(
            "users/new.html",
            user=user_data,
            errors=errors,
        )
    try:
        repo.save(user_data)
        conn.commit()
    except Exception as e:
        conn.rollback()
        flash("Ошибка при добавлении пользователя: " + str(e), "danger")
        return render_template(
            "users/new.html",
            user=user_data,
            errors={"db": "Ошибка при добавлении пользователя"},
        )
    finally:
        conn.close()

    flash("Пользователь успешно добавлен", "success")
    return redirect(url_for("users_get"), code=302)


@app.route("/users/new")
def users_new():
    user = {"name": "", "email": ""}
    errors = {}
    return render_template(
        "users/new.html",
        user=user,
        errors=errors,
    )


@app.route("/users/<id>/edit")
def users_edit(id):
    conn, repo = get_repo()
    try:
        user = repo.find(id)
        errors = {}

        return render_template(
            "users/edit.html",
            user=user,
            errors=errors,
        )
    finally:
        conn.close()


@app.route("/users/<id>/patch", methods=["POST"])
def users_patch(id):
    conn, repo = get_repo()
    user = repo.find(id)
    data = request.form.to_dict()

    errors = validate(data)
    if errors:
        return (
            render_template(
                "users/edit.html",
                user=user,
                errors=errors,
            ),
            422,
        )
    data["id"] = user["id"]
    repo.save(data)
    flash("Пользователь успешно обновлен", "success")
    conn.close()
    return redirect(url_for("users_get"))



@app.route("/users/<id>/delete", methods=["POST"])
def users_delete(id):
    repo, conn = get_repo()
    try:
        repo.destroy(id)
        flash("Пользователь удален", "success")
        return redirect(url_for("users_get"))
    finally:
        conn.close()


@app.route("/users/<id>")
def users_show(id):
    conn, repo = get_repo()
    try:
        user = repo.find(id)
        return render_template(
            "users/show.html",
            user=user,
        )
    finally:
        conn.close()


def validate(user):
    errors = {}
    if not user["name"]:
        errors["name"] = "Can't be blank"
    if not user["email"]:
        errors["email"] = "Can't be blank"
    return errors
