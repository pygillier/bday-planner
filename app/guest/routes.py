from flask import abort, redirect, render_template, request, url_for

from app.emails import send_recap_email
from app.extensions import db
from app.guest import guest_bp
from app.guest.forms import DetailsForm
from app.models import EventOption, Guest, GuestEventLog, PlusOne, utcnow


def _get_guest_or_404(token):
    guest = Guest.query.filter_by(token=token).first()
    if guest is None:
        abort(404)
    return guest


@guest_bp.errorhandler(404)
def invalid_token(_error):
    return render_template("guest/invalid_token.html"), 404


@guest_bp.route("/<token>")
def landing(token):
    guest = _get_guest_or_404(token)
    if guest.rsvp_status == "declined":
        return render_template("guest/landing.html", guest=guest)
    return redirect(url_for("guest.details", token=token))


@guest_bp.route("/<token>/confirmer", methods=["POST"])
def confirm(token):
    guest = _get_guest_or_404(token)
    guest.rsvp_status = "confirmed"
    guest.rsvp_updated_at = utcnow()
    db.session.add(GuestEventLog(guest_id=guest.id, event_type="confirmed"))
    db.session.commit()
    return redirect(url_for("guest.details", token=token))


@guest_bp.route("/<token>/decliner", methods=["POST"])
def decline(token):
    guest = _get_guest_or_404(token)
    guest.rsvp_status = "declined"
    guest.rsvp_updated_at = utcnow()
    db.session.add(GuestEventLog(guest_id=guest.id, event_type="declined"))
    db.session.commit()
    return redirect(url_for("guest.thank_you", token=token))


@guest_bp.route("/<token>/details", methods=["GET", "POST"])
def details(token):
    guest = _get_guest_or_404(token)
    if guest.rsvp_status == "declined":
        return redirect(url_for("guest.landing", token=token))

    was_pending = guest.rsvp_status != "confirmed"
    options = EventOption.query.order_by(EventOption.starts_at).all()
    form = DetailsForm(obj=guest)
    form.set_event_options(options)
    if not guest.email:
        form.require_email()
    if request.method == "GET":
        form.event_option_ids.data = [option.id for option in guest.event_options]

    if form.validate_on_submit():
        if not guest.email:
            guest.email = form.email.data
        guest.dietary_notes = form.dietary_notes.data
        if options:
            selected_ids = set(form.event_option_ids.data)
            guest.event_options = [option for option in options if option.id in selected_ids]
        for plus_one, notes in zip(
            guest.plus_ones, request.form.getlist("plus_one_notes")
        ):
            plus_one.dietary_notes = notes
        guest.rsvp_status = "confirmed"
        guest.rsvp_updated_at = utcnow()
        db.session.add(
            GuestEventLog(
                guest_id=guest.id, event_type="confirmed" if was_pending else "updated"
            )
        )
        is_first_completion = guest.recap_sent_at is None
        if is_first_completion and guest.email:
            guest.recap_sent_at = utcnow()
        db.session.commit()
        if is_first_completion and guest.email:
            send_recap_email(guest)
        return redirect(url_for("guest.thank_you", token=token))

    return render_template("guest/details.html", guest=guest, form=form, options=options)


@guest_bp.route("/<token>/details/plus-one/add", methods=["POST"])
def add_plus_one(token):
    guest = _get_guest_or_404(token)
    db.session.add(PlusOne(guest_id=guest.id))
    db.session.commit()
    return redirect(url_for("guest.details", token=token))


@guest_bp.route("/<token>/details/plus-one/<int:plus_one_id>/remove", methods=["POST"])
def remove_plus_one(token, plus_one_id):
    guest = _get_guest_or_404(token)
    plus_one = PlusOne.query.filter_by(id=plus_one_id, guest_id=guest.id).first()
    if plus_one is not None:
        db.session.delete(plus_one)
        db.session.commit()
    return redirect(url_for("guest.details", token=token))


@guest_bp.route("/<token>/merci")
def thank_you(token):
    guest = _get_guest_or_404(token)
    return render_template("guest/thank_you.html", guest=guest)
