import io
import pandas as pd
from flask import send_file


def export_submissions_to_excel(submissions):
    """
    Takes a list of Submission ORM objects and returns a Flask response
    with an Excel file attachment.
    """
    rows = []
    for sub in submissions:
        rows.append(
            {
                "Name": sub.user.name,
                "College": sub.user.college,
                "Register Number": sub.user.register_number,
                "Language": sub.problem.language.name,
                "Question": sub.problem.problem_name,
                "Attempts": sub.attempts,
                "Time Taken (s)": sub.time_taken,
                "Score": sub.score,
                "Correct": "Yes" if sub.is_correct else "No",
                "Final Code Answer": sub.submitted_code,
            }
        )

    df = pd.DataFrame(rows)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Submissions")
    output.seek(0)

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="debug_event_submissions.xlsx",
    )
