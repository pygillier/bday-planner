from flask import Blueprint

guest_bp = Blueprint("guest", __name__, url_prefix="/rsvp")

from app.guest import routes  # noqa: E402,F401
