"""
utils/helpers.py — Shared utility functions
"""
from flask import abort


def get_doc_or_404(model, **kwargs):
    """
    Fetch a single MongoEngine document matching kwargs.
    Returns the document or calls abort(404) if not found.

    Usage:
        lang = get_doc_or_404(Language, id=lang_id)
    """
    obj = model.objects(**kwargs).first()
    if obj is None:
        abort(404)
    return obj
