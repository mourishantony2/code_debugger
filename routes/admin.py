from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, jsonify
)
from models import Language, Problem, User, Submission, Violation
from utils.excel_export import export_submissions_to_excel
from utils.helpers import get_doc_or_404
from config import Config

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("is_admin"):
            return redirect(url_for("admin.login"))
        return f(*args, **kwargs)
    return decorated


# ── Auth ──────────────────────────────────────────────────────────────────────

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("is_admin"):
        return redirect(url_for("admin.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        if username == Config.ADMIN_USERNAME and password == Config.ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect(url_for("admin.dashboard"))
        flash("Invalid credentials.", "error")

    return render_template("login.html")


@admin_bp.route("/logout")
def logout():
    session.pop("is_admin", None)
    return redirect(url_for("admin.login"))


# ── Dashboard ──────────────────────────────────────────────────────────────────

@admin_bp.route("/")
@admin_required
def dashboard():
    languages = list(Language.objects.order_by("name"))
    problems  = list(Problem.objects.order_by("question_number").select_related(max_depth=1))
    users     = list(User.objects.order_by("-created_at"))

    # ── Submissions: group by user → best submission per question ────────────
    from mongoengine.errors import DoesNotExist

    all_subs_raw = list(
        Submission.objects.order_by("user", "problem", "attempts")
        .select_related(max_depth=2)
    )

    # Filter out submissions whose problem or user was deleted (orphaned DBRefs)
    all_subs = []
    for sub in all_subs_raw:
        try:
            _ = sub.user.id
            _ = sub.problem.id
            _ = sub.problem.language.name
            all_subs.append(sub)
        except DoesNotExist:
            pass

    best_map = {}                           # (user_id, problem_id) → Submission
    for sub in all_subs:
        key      = (str(sub.user.id), str(sub.problem.id))
        existing = best_map.get(key)
        if existing is None:
            best_map[key] = sub
        elif sub.is_correct and not existing.is_correct:
            best_map[key] = sub
        elif sub.is_correct == existing.is_correct and sub.attempts > existing.attempts:
            best_map[key] = sub

    user_groups = {}
    for sub in best_map.values():
        uid = str(sub.user.id)
        if uid not in user_groups:
            user_groups[uid] = {"user": sub.user, "subs": [], "total_score": 0.0, "solved": 0}
        user_groups[uid]["subs"].append(sub)
        if sub.is_correct:
            user_groups[uid]["total_score"] += sub.score
            user_groups[uid]["solved"]      += 1

    for grp in user_groups.values():
        grp["subs"].sort(key=lambda s: (s.problem.language.name, s.problem.question_number))

    submission_groups = sorted(user_groups.values(), key=lambda g: g["user"].name)

    # ── Leaderboard (aggregation pipeline) ───────────────────────────────────
    pipeline = [
        {"$match": {"is_correct": True}},
        {"$group": {
            "_id":                "$user",
            "total_score":        {"$sum": "$score"},
            "total_submissions":  {"$sum": 1},
        }},
        {"$sort": {"total_score": -1}},
        {"$limit": 100},
    ]
    raw_lb     = list(Submission.objects.aggregate(pipeline))
    leaderboard = []
    for row in raw_lb:
        u = User.objects(id=row["_id"]).first()
        if u:
            leaderboard.append({
                "name":              u.name,
                "college":           u.college,
                "register_number":   u.register_number,
                "total_score":       row["total_score"],
                "total_submissions": row["total_submissions"],
            })

    # ── Violations ────────────────────────────────────────────────────────────
    # Safely resolve violations — any whose user/problem was deleted are excluded
    violations_raw = list(Violation.objects.order_by("-created_at").select_related(max_depth=2))
    violations = []
    for v in violations_raw:
        try:
            _ = v.user.id          # ensure user still exists
            # For problem: set to None if it's an orphaned reference
            if v.problem is not None:
                try:
                    _ = v.problem.id
                    _ = v.problem.language.name
                except DoesNotExist:
                    v.problem = None   # nullify the broken reference
            violations.append(v)
        except DoesNotExist:
            pass                   # skip violations whose user was also deleted

    return render_template(
        "admin_dashboard.html",
        languages=languages,
        problems=problems,
        users=users,
        submission_groups=submission_groups,
        leaderboard=leaderboard,
        violations=violations,
    )


# ── Languages ─────────────────────────────────────────────────────────────────

@admin_bp.route("/language/add", methods=["POST"])
@admin_required
def add_language():
    name = request.form.get("language_name", "").strip()
    if not name:
        flash("Language name required.", "error")
        return redirect(url_for("admin.dashboard"))
    if Language.objects(name=name).first():
        flash(f"Language '{name}' already exists.", "error")
        return redirect(url_for("admin.dashboard"))
    Language(name=name).save()
    flash(f"Language '{name}' added.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/language/<lang_id>/toggle", methods=["POST"])
@admin_required
def toggle_language(lang_id):
    lang = get_doc_or_404(Language, id=lang_id)
    lang.is_active = not lang.is_active
    lang.save()
    status = "enabled (visible to participants)" if lang.is_active else "hidden from participants"
    flash(f"Language '{lang.name}' is now {status}.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/language/<lang_id>/delete", methods=["POST"])
@admin_required
def delete_language(lang_id):
    lang = get_doc_or_404(Language, id=lang_id)
    # Cascade: delete problems for this language
    Problem.objects(language=lang).delete()
    lang.delete()
    flash(f"Language '{lang.name}' deleted.", "success")
    return redirect(url_for("admin.dashboard"))


# ── Problems ──────────────────────────────────────────────────────────────────

@admin_bp.route("/problem/add", methods=["GET", "POST"])
@admin_required
def add_problem():
    languages = Language.objects(is_active=True)

    if request.method == "POST":
        lang_id         = request.form.get("language_id")
        problem_name    = request.form.get("problem_name", "").strip()
        error_code      = request.form.get("error_code", "").strip()
        correct_code    = request.form.get("correct_code", "").strip()
        expected_output = request.form.get("expected_output", "").strip()
        time_limit      = int(request.form.get("time_limit", 300))
        question_number = int(request.form.get("question_number", 1))

        if not all([lang_id, problem_name, error_code, correct_code, expected_output]):
            flash("All fields are required.", "error")
            return render_template("add_problem.html", languages=languages, problem=None)

        lang = get_doc_or_404(Language, id=lang_id)
        Problem(
            language=lang,
            problem_name=problem_name,
            error_code=error_code,
            correct_code=correct_code,
            expected_output=expected_output,
            time_limit=time_limit,
            question_number=question_number,
        ).save()
        flash(f"Problem '{problem_name}' added.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("add_problem.html", languages=languages, problem=None)


@admin_bp.route("/problem/<prob_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_problem(prob_id):
    problem   = get_doc_or_404(Problem, id=prob_id)
    languages = Language.objects(is_active=True)

    if request.method == "POST":
        lang = get_doc_or_404(Language, id=request.form.get("language_id"))
        problem.language        = lang
        problem.problem_name    = request.form.get("problem_name", "").strip()
        problem.error_code      = request.form.get("error_code", "").strip()
        problem.correct_code    = request.form.get("correct_code", "").strip()
        problem.expected_output = request.form.get("expected_output", "").strip()
        problem.time_limit      = int(request.form.get("time_limit", problem.time_limit))
        problem.question_number = int(request.form.get("question_number", problem.question_number))
        problem.save()
        flash(f"Problem '{problem.problem_name}' updated.", "success")
        return redirect(url_for("admin.dashboard"))

    return render_template("add_problem.html", languages=languages, problem=problem)


@admin_bp.route("/problem/<prob_id>/delete", methods=["POST"])
@admin_required
def delete_problem(prob_id):
    problem = get_doc_or_404(Problem, id=prob_id)
    name    = problem.problem_name
    problem.delete()
    flash(f"Problem '{name}' deleted.", "success")
    return redirect(url_for("admin.dashboard"))


# ── Export ────────────────────────────────────────────────────────────────────

@admin_bp.route("/export")
@admin_required
def export():
    submissions = list(Submission.objects.select_related(max_depth=2))
    return export_submissions_to_excel(submissions)
