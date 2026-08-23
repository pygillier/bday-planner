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
from app.admin.csv_import import import_guests_from_csv
from app.admin.forms import EmailTemplateForm, EventOptionForm, GuestForm, ImportForm
from app.emails import (
    preview_context,
    render_invitation_body,
    render_invitation_subject,
    send_invitation_email,
    send_test_email,
)
from app.extensions import db, oauth
from app.models import EMAIL_VARIABLES, EmailTemplate, EventOption, Guest, GuestEventLog

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

    options = EventOption.query.order_by(EventOption.starts_at).all()
    date_breakdown = [
        (option, sum(g.headcount for g in guests if option in g.event_options))
        for option in options
    ]
    best_date = None
    if date_breakdown:
        top_option, top_headcount = max(date_breakdown, key=lambda pair: pair[1])
        if top_headcount > 0:
            best_date = (top_option, top_headcount)

    return render_template(
        "admin/dashboard.html",
        counts=counts,
        total_headcount=total_headcount,
        date_breakdown=date_breakdown,
        best_date=best_date,
    )


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


@admin_bp.route("/guests/import", methods=["GET", "POST"])
def import_guests():
    form = ImportForm()
    if form.validate_on_submit():
        result = import_guests_from_csv(form.csv_file.data.stream.read())

        if result.added:
            flash(f"{result.added} invité·e(s) importé·e(s).", "success")
        if result.skipped_duplicate:
            flash(
                f"{result.skipped_duplicate} ligne(s) ignorée(s) (déjà présent·e·s).", "success"
            )
        for error in result.errors[:10]:
            flash(error, "error")

        if result.added or result.skipped_duplicate:
            return redirect(url_for("admin.guests_list"))

    return render_template("admin/import_guests.html", form=form)


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


@admin_bp.route("/email-template", methods=["GET", "POST"])
def email_template():
    template = EmailTemplate.get_current()
    form = EmailTemplateForm(obj=template)
    action = request.form.get("action")

    if form.validate_on_submit():
        if action == "test":
            if not form.test_email.data:
                flash("Indiquez une adresse e-mail pour l'envoi de test.", "error")
            elif send_test_email(
                form.test_email.data, form.subject.data, form.body.data, form.signature.data
            ):
                flash(f"E-mail de test envoyé à {form.test_email.data}.", "success")
            else:
                flash("Échec de l'envoi de l'e-mail de test.", "error")
        else:
            template.subject = form.subject.data
            template.body = form.body.data
            template.signature = form.signature.data or ""
            db.session.commit()
            flash("Modèle d'e-mail mis à jour.", "success")
            return redirect(url_for("admin.email_template"))

    context = preview_context()
    preview_subject = render_invitation_subject(form.subject.data or template.subject, context)
    preview_body = render_invitation_body(form.body.data or template.body, context)
    preview_signature = render_invitation_body(
        form.signature.data if form.signature.data is not None else template.signature, context
    )

    return render_template(
        "admin/email_template.html",
        form=form,
        variables=EMAIL_VARIABLES,
        preview_subject=preview_subject,
        preview_body=preview_body,
        preview_signature=preview_signature,
    )


@admin_bp.route("/dates")
def event_options_list():
    options = EventOption.query.order_by(EventOption.starts_at).all()
    return render_template("admin/event_options.html", options=options)


@admin_bp.route("/dates/new", methods=["GET", "POST"])
def new_event_option():
    form = EventOptionForm()
    if form.validate_on_submit():
        option = EventOption()
        form.populate_obj(option)
        db.session.add(option)
        db.session.commit()
        flash("Date ajoutée.", "success")
        return redirect(url_for("admin.event_options_list"))
    return render_template("admin/event_option_form.html", form=form, option=None)


@admin_bp.route("/dates/<int:option_id>/edit", methods=["GET", "POST"])
def edit_event_option(option_id):
    option = EventOption.query.get_or_404(option_id)
    form = EventOptionForm(obj=option)
    if form.validate_on_submit():
        form.populate_obj(option)
        db.session.commit()
        flash("Date mise à jour.", "success")
        return redirect(url_for("admin.event_options_list"))
    return render_template("admin/event_option_form.html", form=form, option=option)


@admin_bp.route("/dates/<int:option_id>/delete", methods=["POST"])
def delete_event_option(option_id):
    option = EventOption.query.get_or_404(option_id)
    if option.guests:
        flash(
            "Impossible de supprimer cette date : des invité·e·s l'ont déjà choisie.",
            "error",
        )
    else:
        db.session.delete(option)
        db.session.commit()
        flash("Date supprimée.", "success")
    return redirect(url_for("admin.event_options_list"))


@admin_bp.route("/journal")
def journal():
    entries = (
        GuestEventLog.query.join(Guest)
        .order_by(GuestEventLog.created_at.desc())
        .limit(200)
        .all()
    )
    return render_template("admin/journal.html", entries=entries)


@admin_bp.route("/export.csv")
def export_csv():
    guests = Guest.query.order_by(Guest.last_name, Guest.first_name).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["Nom", "Statut", "Dates disponibles", "Allergies / notes", "Accompagnant", "Allergies accompagnant"]
    )
    for guest in guests:
        event_date = ", ".join(option.display_text for option in guest.event_options)
        if guest.plus_ones:
            for index, plus_one in enumerate(guest.plus_ones, start=1):
                writer.writerow(
                    [
                        guest.full_name,
                        guest.rsvp_status,
                        event_date,
                        guest.dietary_notes or "",
                        f"Accompagnant {index}",
                        plus_one.dietary_notes or "",
                    ]
                )
        else:
            writer.writerow(
                [guest.full_name, guest.rsvp_status, event_date, guest.dietary_notes or "", "", ""]
            )

    return Response(
        buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=invites-80ans.csv"},
    )
