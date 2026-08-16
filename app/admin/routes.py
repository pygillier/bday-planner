import csv
import io
import secrets

from flask import (
    Response,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.admin import admin_bp
from app.admin.forms import GuestForm
from app.emails import send_invitation_email
from app.extensions import db, oauth
from app.models import Guest

PUBLIC_ENDPOINTS = {"admin.login", "admin.login_pocketid", "admin.auth_callback"}


@admin_bp.before_request
def require_login():
    if request.endpoint in PUBLIC_ENDPOINTS:
        return None
    if not session.get("admin_sub"):
        return redirect(url_for("admin.login"))
    return None


@admin_bp.route("/login")
def login():
    if session.get("admin_sub"):
        return redirect(url_for("admin.dashboard"))
    return render_template("admin/login.html")


@admin_bp.route("/login/pocketid")
def login_pocketid():
    redirect_uri = url_for("admin.auth_callback", _external=True)
    return oauth.pocketid.authorize_redirect(redirect_uri)


@admin_bp.route("/auth/callback")
def auth_callback():
    token = oauth.pocketid.authorize_access_token()
    userinfo = token.get("userinfo") or oauth.pocketid.parse_id_token(token)
    session["admin_sub"] = userinfo["sub"]
    session["admin_email"] = userinfo.get("email")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("admin.login"))


@admin_bp.route("/")
def dashboard():
    guests = Guest.query.all()
    counts = {
        "confirmed": sum(1 for g in guests if g.rsvp_status == "confirmed"),
        "declined": sum(1 for g in guests if g.rsvp_status == "declined"),
        "pending": sum(1 for g in guests if g.rsvp_status == "pending"),
    }
    total_headcount = sum(g.headcount for g in guests)
    return render_template("admin/dashboard.html", counts=counts, total_headcount=total_headcount)


@admin_bp.route("/guests")
def guests_list():
    status_filter = request.args.get("status")
    query = Guest.query
    if status_filter in {"pending", "confirmed", "declined"}:
        query = query.filter_by(rsvp_status=status_filter)
    guests = query.order_by(Guest.last_name, Guest.first_name).all()
    return render_template("admin/guests_list.html", guests=guests, status_filter=status_filter)


@admin_bp.route("/guests/new", methods=["GET", "POST"])
def new_guest():
    form = GuestForm()
    if form.validate_on_submit():
        guest = Guest()
        form.populate_obj(guest)
        db.session.add(guest)
        db.session.commit()
        flash("Invité·e ajouté·e.", "success")
        return redirect(url_for("admin.guests_list"))
    return render_template("admin/guest_form.html", form=form, guest=None)


@admin_bp.route("/guests/<int:guest_id>/edit", methods=["GET", "POST"])
def edit_guest(guest_id):
    guest = Guest.query.get_or_404(guest_id)
    form = GuestForm(obj=guest)
    if form.validate_on_submit():
        form.populate_obj(guest)
        db.session.commit()
        flash("Fiche mise à jour.", "success")
        return redirect(url_for("admin.guests_list"))
    return render_template("admin/guest_form.html", form=form, guest=guest)


@admin_bp.route("/guests/<int:guest_id>/delete", methods=["POST"])
def delete_guest(guest_id):
    guest = Guest.query.get_or_404(guest_id)
    db.session.delete(guest)
    db.session.commit()
    flash("Invité·e supprimé·e.", "success")
    return redirect(url_for("admin.guests_list"))


@admin_bp.route("/guests/<int:guest_id>/send-invitation", methods=["POST"])
def send_invitation(guest_id):
    guest = Guest.query.get_or_404(guest_id)
    if not guest.email:
        flash("Cet·te invité·e n'a pas d'adresse e-mail — transmettez le lien manuellement.", "error")
    elif send_invitation_email(guest):
        flash(f"Invitation envoyée à {guest.full_name}.", "success")
    else:
        flash(f"Échec de l'envoi à {guest.full_name}.", "error")
    return redirect(url_for("admin.guests_list"))


@admin_bp.route("/guests/send-invitations", methods=["POST"])
def send_invitations():
    guests = Guest.query.filter(
        Guest.invitation_sent_at.is_(None), Guest.email.isnot(None)
    ).all()
    sent = sum(1 for guest in guests if send_invitation_email(guest))
    failed = len(guests) - sent
    flash(f"{sent} invitation(s) envoyée(s), {failed} échec(s).", "success" if failed == 0 else "error")
    return redirect(url_for("admin.guests_list"))


@admin_bp.route("/guests/<int:guest_id>/regenerate-link", methods=["POST"])
def regenerate_link(guest_id):
    guest = Guest.query.get_or_404(guest_id)
    guest.token = secrets.token_urlsafe(32)
    guest.invitation_sent_at = None
    db.session.commit()
    flash("Lien régénéré — pensez à le retransmettre.", "success")
    return redirect(url_for("admin.guests_list"))


@admin_bp.route("/export.csv")
def export_csv():
    guests = Guest.query.order_by(Guest.last_name, Guest.first_name).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Nom", "Statut", "Allergies / notes", "Accompagnant", "Allergies accompagnant"])
    for guest in guests:
        if guest.plus_ones:
            for index, plus_one in enumerate(guest.plus_ones, start=1):
                writer.writerow(
                    [
                        guest.full_name,
                        guest.rsvp_status,
                        guest.dietary_notes or "",
                        f"Accompagnant {index}",
                        plus_one.dietary_notes or "",
                    ]
                )
        else:
            writer.writerow([guest.full_name, guest.rsvp_status, guest.dietary_notes or "", "", ""])

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=invites-80ans.csv"},
    )
