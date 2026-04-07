import re
from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, jsonify
)
from models import Language, Problem, Submission, User, Violation
from utils.scoring import calculate_score
from utils.helpers import get_doc_or_404

exam_bp   = Blueprint("exam", __name__, url_prefix="/exam")
MAX_ATTEMPTS = 5


def user_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.register"))
        return f(*args, **kwargs)
    return decorated


def normalize_code(code: str) -> str:
    """
    Compare code preserving indentation:
      - Normalise CRLF → LF
      - Strip trailing whitespace per line  (trailing spaces don't matter)
      - Preserve leading whitespace         (indentation IS significant)
      - Remove blank lines at very top/bottom only
      - Case-sensitive
    """
    code  = code.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in code.split("\n")]
    while lines and lines[0]  == "": lines.pop(0)
    while lines and lines[-1] == "": lines.pop()
    return "\n".join(lines)


def _get_user():
    """Return the current User document or None."""
    uid = session.get("user_id")
    return User.objects(id=uid).first() if uid else None


# ── Language Selection ────────────────────────────────────────────────────────

@exam_bp.route("/select")
@user_required
def language_select():
    languages = Language.objects(is_active=True)
    user_id   = session["user_id"]

    completed_lang_ids = set()
    for lang in languages:
        problems = Problem.objects(language=lang).order_by("question_number")
        if problems.count() > 0:
            all_done = all(
                Submission.objects(user=user_id, problem=p, is_correct=True).first()
                for p in problems
            )
            if all_done:
                completed_lang_ids.add(lang.id)

    return render_template(
        "language_select.html",
        languages=languages,
        completed_lang_ids=completed_lang_ids,
    )


# ── Exam Question ─────────────────────────────────────────────────────────────

@exam_bp.route("/start/<lang_id>")
@user_required
def start_language(lang_id):
    user_id  = session["user_id"]
    lang     = get_doc_or_404(Language, id=lang_id)
    problems = Problem.objects(language=lang).order_by("question_number")

    if not problems:
        flash("No questions available for this language.", "error")
        return redirect(url_for("exam.language_select"))

    for problem in problems:
        if not Submission.objects(user=user_id, problem=problem, is_correct=True).first():
            if Submission.objects(user=user_id, problem=problem, is_correct=False).count() < MAX_ATTEMPTS:
                return redirect(url_for("exam.question", lang_id=lang_id, prob_id=str(problem.id)))

    flash("You have completed all questions for this language!", "success")
    return redirect(url_for("exam.language_select"))


@exam_bp.route("/question/<lang_id>/<prob_id>")
@user_required
def question(lang_id, prob_id):
    user_id  = session["user_id"]
    problem  = get_doc_or_404(Problem, id=prob_id)
    lang     = get_doc_or_404(Language, id=lang_id)

    all_problems    = list(Problem.objects(language=lang).order_by("question_number"))
    total_questions = len(all_problems)
    current_index   = next((i + 1 for i, p in enumerate(all_problems) if p.id == problem.id), 1)

    wrong_attempts = Submission.objects(user=user_id, problem=problem, is_correct=False).count()
    attempts_left  = MAX_ATTEMPTS - wrong_attempts

    if Submission.objects(user=user_id, problem=problem, is_correct=True).first():
        return redirect(url_for("exam.start_language", lang_id=lang_id))

    if attempts_left <= 0:
        return redirect(url_for("exam.start_language", lang_id=lang_id))

    return render_template(
        "exam.html",
        problem=problem,
        lang=lang,
        current_index=current_index,
        total_questions=total_questions,
        attempts_used=wrong_attempts,
        attempts_left=attempts_left,
        max_attempts=MAX_ATTEMPTS,
    )


# ── Submit ────────────────────────────────────────────────────────────────────

@exam_bp.route("/submit", methods=["POST"])
@user_required
def submit():
    data           = request.get_json()
    user_id        = session["user_id"]
    prob_id        = data.get("problem_id")
    lang_id        = data.get("lang_id")
    submitted_code = data.get("code", "")
    time_taken     = float(data.get("time_taken", 0))

    problem = get_doc_or_404(Problem, id=prob_id)

    wrong_attempts = Submission.objects(user=user_id, problem=problem, is_correct=False).count()

    if Submission.objects(user=user_id, problem=problem, is_correct=True).first():
        return jsonify({"status": "already_solved"})

    total_attempts = wrong_attempts + 1

    if total_attempts > MAX_ATTEMPTS:
        return jsonify({"status": "max_attempts", "message": "Maximum attempts reached."})

    is_correct = normalize_code(submitted_code) == normalize_code(problem.correct_code)
    score      = calculate_score(problem.time_limit, time_taken, wrong_attempts) if is_correct else 0.0

    Submission(
        user=user_id,
        problem=problem,
        attempts=total_attempts,
        time_taken=time_taken,
        submitted_code=submitted_code,
        is_correct=is_correct,
        score=score,
    ).save()

    attempts_left = MAX_ATTEMPTS - total_attempts

    if is_correct:
        return jsonify({
            "status": "correct",
            "score": score,
            "expected_output": problem.expected_output,
            "lang_id": lang_id,
        })
    elif attempts_left <= 0:
        return jsonify({
            "status": "max_attempts",
            "message": "Maximum attempts reached. Moving to next question.",
            "lang_id": lang_id,
        })
    else:
        return jsonify({
            "status": "wrong",
            "attempts_left": attempts_left,
            "max_attempts": MAX_ATTEMPTS,
        })


# ── Violation Logging ─────────────────────────────────────────────────────────

@exam_bp.route("/violation", methods=["POST"])
def log_violation():
    """
    Called by security.js (with keepalive:true) just before the participant
    is logged out due to tab-switch or fullscreen-exit.
    Records the event so admin can see it.
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"status": "ignored"})

    data           = request.get_json(silent=True) or {}
    violation_type = data.get("violation_type", "tab_switch")
    prob_id        = data.get("problem_id")

    # Validate violation_type
    if violation_type not in ("tab_switch", "fullscreen_exit"):
        violation_type = "tab_switch"

    user    = User.objects(id=user_id).first()
    problem = Problem.objects(id=prob_id).first() if prob_id else None

    if user:
        Violation(user=user, violation_type=violation_type, problem=problem).save()

    return jsonify({"status": "recorded"})


# ── Completion ────────────────────────────────────────────────────────────────

@exam_bp.route("/complete")
@user_required
def complete():
    user_id    = session["user_id"]
    user       = User.objects(id=user_id).first()
    subs       = list(Submission.objects(user=user_id, is_correct=True).select_related(max_depth=2))
    total_score = round(sum(s.score for s in subs), 2)
    return render_template("complete.html", user=user, total_score=total_score, submissions=subs)
