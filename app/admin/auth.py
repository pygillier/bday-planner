from functools import wraps

from flask import redirect, session, url_for


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_sub"):
            return redirect(url_for("admin.login"))
        return view(*args, **kwargs)

    return wrapped
