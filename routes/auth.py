import secrets
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/", methods=["GET", "POST"])
def register():
    """Participant registration — creates user document and sets session."""
    if request.method == "POST":
        name            = request.form.get("name", "").strip()
        college         = request.form.get("college", "").strip()
        register_number = request.form.get("register_number", "").strip()

        if not name or not college or not register_number:
            flash("All fields are required.", "error")
            return render_template("register.html")

        token = secrets.token_hex(32)
        user  = User(
            name=name,
            college=college,
            register_number=register_number,
            session_token=token,
        )
        user.save()

        session["user_id"]       = str(user.id)
        session["user_name"]     = user.name
        session["session_token"] = token
        session.permanent        = True

        return redirect(url_for("exam.language_select"))

    return render_template("register.html")


@auth_bp.route("/logout")
def logout():
    """Clear user session and redirect to registration."""
    session.clear()
    return redirect(url_for("auth.register"))
