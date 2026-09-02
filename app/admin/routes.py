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
from app.admin.forms import (
    DetailsPageMessageForm,
    EmailTemplateForm,
    EventOptionForm,
    GuestForm,
    ImportForm,
    RecapEmailTemplateForm,
    SmsTemplateForm,
)
from app.emails import (
    preview_context,
    recap_preview_context,
    render_invitation_body,
    render_invitation_subject,
    send_invitation_email,
    send_test_email,
    send_test_recap_email,
)
from app.extensions import db, oauth
from app.models import (
    DETAILS_MESSAGE_VARIABLES,
    EMAIL_VARIABLES,
    RECAP_EMAIL_VARIABLES,
    SMS_VARIABLES,
    DetailsPageMessage,
    EmailTemplate,
    EventOption,
    Guest,
    GuestEventLog,
    InvitationLog,
    RecapEmailTemplate,
    SmsTemplate,
)
from app.sms import render_sms_body, send_invitation_sms, send_test_sms, sms_preview_context

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


def _send_invitation_all_channels(guest):
    """Send the invitation via every channel the guest has contact info
    for. Returns (attempted, sent) counts."""
    attempted = 0
    sent = 0
    if guest.email:
        attempted += 1
        sent += send_invitation_email(guest)
    if guest.phone:
        attempted += 1
        sent += send_invitation_sms(guest)
    return attempted, sent


@admin_bp.route("/guests/<int:guest_id>/send-invitation", methods=["POST"])
def send_invitation(guest_id):
    guest = Guest.query.get_or_404(guest_id)
    attempted, sent = _send_invitation_all_channels(guest)
    if attempted == 0:
        flash(
            "Cet·te invité·e n'a ni adresse e-mail ni numéro de téléphone — transmettez le lien manuellement.",
            "error",
        )
    elif sent == attempted:
        flash(f"Invitation envoyée à {guest.full_name}.", "success")
    else:
        flash(f"Échec partiel de l'envoi à {guest.full_name} ({sent}/{attempted}).", "error")
    return redirect(url_for("admin.guests_list"))


@admin_bp.route("/guests/send-invitations", methods=["POST"])
def send_invitations():
    guests = Guest.query.filter(
        Guest.invitation_sent_at.is_(None),
        db.or_(Guest.email.isnot(None), Guest.phone.isnot(None)),
    ).all()
    attempted = 0
    sent = 0
    for guest in guests:
        guest_attempted, guest_sent = _send_invitation_all_channels(guest)
        attempted += guest_attempted
        sent += guest_sent
    failed = attempted - sent
    flash(f"{sent} invitation(s) envoyée(s), {failed} échec(s).", "success" if failed == 0 else "error")
    return redirect(url_for("admin.guests_list"))


@admin_bp.route("/guests/<int:guest_id>/reset-answer", methods=["POST"])
def reset_answer(guest_id):
    guest = Guest.query.get_or_404(guest_id)
    guest.rsvp_status = "pending"
    guest.rsvp_updated_at = None
    guest.dietary_notes = None
    guest.event_options = []
    guest.recap_sent_at = None
    for plus_one in list(guest.plus_ones):
        db.session.delete(plus_one)
    db.session.add(GuestEventLog(guest_id=guest.id, event_type="reset"))
    db.session.commit()
    flash(f"Réponse de {guest.full_name} réinitialisée.", "success")
    return redirect(url_for("admin.guests_list"))


@admin_bp.route("/guests/<int:guest_id>/regenerate-link", methods=["POST"])
def regenerate_link(guest_id):
    guest = Guest.query.get_or_404(guest_id)
    guest.token = secrets.token_urlsafe(6)
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


@admin_bp.route("/recap-email-template", methods=["GET", "POST"])
def recap_email_template():
    template = RecapEmailTemplate.get_current()
    form = RecapEmailTemplateForm(obj=template)
    action = request.form.get("action")

    if form.validate_on_submit():
        if action == "test":
            if not form.test_email.data:
                flash("Indiquez une adresse e-mail pour l'envoi de test.", "error")
            elif send_test_recap_email(
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
            return redirect(url_for("admin.recap_email_template"))

    context = recap_preview_context()
    preview_subject = render_invitation_subject(form.subject.data or template.subject, context)
    preview_body = render_invitation_body(form.body.data or template.body, context)
    preview_signature = render_invitation_body(
        form.signature.data if form.signature.data is not None else template.signature, context
    )

    return render_template(
        "admin/recap_email_template.html",
        form=form,
        variables=RECAP_EMAIL_VARIABLES,
        preview_subject=preview_subject,
        preview_body=preview_body,
        preview_signature=preview_signature,
    )


@admin_bp.route("/sms-template", methods=["GET", "POST"])
def sms_template():
    template = SmsTemplate.get_current()
    form = SmsTemplateForm(obj=template)
    action = request.form.get("action")

    if form.validate_on_submit():
        if action == "test":
            if not form.test_phone.data:
                flash("Indiquez un numéro de téléphone pour l'envoi de test.", "error")
            elif send_test_sms(form.test_phone.data, form.body.data, form.signature.data):
                flash(f"SMS de test envoyé à {form.test_phone.data}.", "success")
            else:
                flash("Échec de l'envoi du SMS de test.", "error")
        else:
            template.body = form.body.data
            template.signature = form.signature.data or ""
            db.session.commit()
            flash("Modèle de SMS mis à jour.", "success")
            return redirect(url_for("admin.sms_template"))

    context = sms_preview_context()
    preview_body = render_sms_body(form.body.data or template.body, context)
    preview_signature = render_sms_body(
        form.signature.data if form.signature.data is not None else template.signature, context
    )

    return render_template(
        "admin/sms_template.html",
        form=form,
        variables=SMS_VARIABLES,
        preview_body=preview_body,
        preview_signature=preview_signature,
        preview_context=context,
    )


@admin_bp.route("/details-message", methods=["GET", "POST"])
def details_message():
    message = DetailsPageMessage.get_current()
    form = DetailsPageMessageForm(obj=message)

    if form.validate_on_submit():
        message.body = form.body.data or ""
        db.session.commit()
        flash("Message mis à jour.", "success")
        return redirect(url_for("admin.details_message"))

    context = preview_context()
    preview_body = render_invitation_body(form.body.data or message.body, context)

    return render_template(
        "admin/details_message.html",
        form=form,
        variables=DETAILS_MESSAGE_VARIABLES,
        preview_body=preview_body,
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
    guest_id = request.args.get("guest_id", type=int)
    guest = None

    event_query = GuestEventLog.query.join(Guest)
    invitation_query = InvitationLog.query.join(Guest)
    if guest_id is not None:
        guest = Guest.query.get_or_404(guest_id)
        event_query = event_query.filter(GuestEventLog.guest_id == guest_id)
        invitation_query = invitation_query.filter(InvitationLog.guest_id == guest_id)

    entries = [(e.guest, e.label, e.created_at) for e in event_query] + [
        (i.guest, i.label, i.sent_at) for i in invitation_query
    ]
    entries.sort(key=lambda entry: entry[2], reverse=True)
    if guest_id is None:
        entries = entries[:200]

    return render_template("admin/journal.html", entries=entries, guest=guest)


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
