"""
models.py — MongoEngine document definitions for MongoDB Atlas.

Collections:
  languages, problems, users, submissions, violations
"""
from datetime import datetime
import mongoengine as me


class Language(me.Document):
    name       = me.StringField(unique=True, required=True, max_length=50)
    is_active  = me.BooleanField(default=True)
    created_at = me.DateTimeField(default=datetime.utcnow)

    meta = {"collection": "languages", "ordering": ["name"]}

    def __str__(self):
        return self.name


class Problem(me.Document):
    language        = me.ReferenceField(Language, required=True)
    problem_name    = me.StringField(required=True, max_length=200)
    error_code      = me.StringField(required=True)
    correct_code    = me.StringField(required=True)
    expected_output = me.StringField(required=True)
    time_limit      = me.IntField(default=300)      # seconds
    question_number = me.IntField(required=True)
    created_at      = me.DateTimeField(default=datetime.utcnow)

    meta = {"collection": "problems", "ordering": ["question_number"]}

    def __str__(self):
        return self.problem_name


class User(me.Document):
    name            = me.StringField(required=True, max_length=150)
    college         = me.StringField(required=True, max_length=200)
    register_number = me.StringField(required=True, max_length=100)
    session_token   = me.StringField(unique=True, required=True, max_length=64)
    created_at      = me.DateTimeField(default=datetime.utcnow)

    meta = {"collection": "users", "ordering": ["-created_at"]}

    def __str__(self):
        return self.name


class Submission(me.Document):
    user           = me.ReferenceField(User,    required=True)
    problem        = me.ReferenceField(Problem, required=True)
    attempts       = me.IntField(default=1)
    time_taken     = me.FloatField(default=0)   # seconds elapsed
    submitted_code = me.StringField(required=True)
    is_correct     = me.BooleanField(default=False)
    score          = me.FloatField(default=0)
    created_at     = me.DateTimeField(default=datetime.utcnow)

    meta = {"collection": "submissions", "ordering": ["-created_at"]}


class Violation(me.Document):
    """Recorded whenever a participant exits fullscreen or switches tabs."""
    VIOLATION_CHOICES = ("tab_switch", "fullscreen_exit")

    user           = me.ReferenceField(User,    required=True)
    violation_type = me.StringField(required=True, choices=VIOLATION_CHOICES)
    problem        = me.ReferenceField(Problem, null=True)   # question they were on
    created_at     = me.DateTimeField(default=datetime.utcnow)

    meta = {"collection": "violations", "ordering": ["-created_at"]}
