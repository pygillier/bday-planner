from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import (
    BooleanField,
    DateTimeLocalField,
    SelectField,
    SelectMultipleField,
    StringField,
    TextAreaField,
    widgets,
)
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError

from app.phone import to_e164_fr


class GuestForm(FlaskForm):
    first_name = StringField("Prénom", validators=[DataRequired(), Length(max=120)])
    last_name = StringField("Nom", validators=[DataRequired(), Length(max=120)])
    email = StringField("E-mail", validators=[Optional(), Email(), Length(max=255)])
    phone = StringField("Téléphone", validators=[Optional(), Length(max=50)])

    def validate_phone(self, field):
        if field.data and to_e164_fr(field.data) is None:
            raise ValidationError("Numéro français invalide (ex : 06 12 34 56 78).")


class ImportForm(FlaskForm):
    csv_file = FileField(
        "Fichier CSV",
        validators=[FileRequired(), FileAllowed(["csv"], "Fichier CSV uniquement.")],
    )


class EventOptionForm(FlaskForm):
    label = StringField("Intitulé (facultatif)", validators=[Optional(), Length(max=255)])
    starts_at = DateTimeLocalField(
        "Date et heure", format="%Y-%m-%dT%H:%M", validators=[DataRequired()]
    )


class EmailTemplateForm(FlaskForm):
    subject = StringField("Objet de l'e-mail", validators=[DataRequired(), Length(max=255)])
    body = TextAreaField("Message", validators=[DataRequired(), Length(max=5000)])
    signature = TextAreaField(
        "Signature (facultatif, affichée après le bouton)",
        validators=[Optional(), Length(max=2000)],
    )
    test_email = StringField("Adresse de test", validators=[Optional(), Email(), Length(max=255)])


class SmsTemplateForm(FlaskForm):
    body = TextAreaField("Message", validators=[DataRequired(), Length(max=1000)])
    signature = TextAreaField("Signature (facultatif)", validators=[Optional(), Length(max=200)])
    test_phone = StringField("Numéro de test", validators=[Optional(), Length(max=50)])

    def validate_test_phone(self, field):
        if field.data and to_e164_fr(field.data) is None:
            raise ValidationError("Numéro français invalide (ex : 06 12 34 56 78).")


class DetailsPageMessageForm(FlaskForm):
    body = TextAreaField(
        "Message (facultatif, affiché en haut de la page)",
        validators=[Optional(), Length(max=2000)],
    )


class FollowUpComposeForm(FlaskForm):
    status_filter = SelectField(
        "Statut RSVP",
        choices=[("confirmed", "Disponible"), ("declined", "Indisponible")],
        validators=[DataRequired()],
    )
    channel_email = BooleanField("E-mail", default=True)
    channel_sms = BooleanField("SMS")
    subject = StringField("Objet (e-mail uniquement)", validators=[Optional(), Length(max=255)])
    body = TextAreaField(
        "Message (Markdown : **gras**, *italique*, listes avec -, liens [texte](url))",
        validators=[DataRequired(), Length(max=5000)],
    )
    guest_ids = SelectMultipleField(
        "Destinataires",
        coerce=int,
        option_widget=widgets.CheckboxInput(),
        widget=widgets.ListWidget(prefix_label=False),
    )
    test_email = StringField("E-mail de test", validators=[Optional(), Email(), Length(max=255)])
    test_phone = StringField("Téléphone de test", validators=[Optional(), Length(max=50)])

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False
        if not self.channel_email.data and not self.channel_sms.data:
            self.channel_email.errors.append("Choisissez au moins un canal (e-mail ou SMS).")
            return False
        if self.channel_email.data and not self.subject.data:
            self.subject.errors.append("L'objet est requis pour l'envoi par e-mail.")
            return False
        return True

    def validate_test_phone(self, field):
        if field.data and to_e164_fr(field.data) is None:
            raise ValidationError("Numéro français invalide (ex : 06 12 34 56 78).")


class RecapEmailTemplateForm(FlaskForm):
    subject = StringField("Objet de l'e-mail", validators=[DataRequired(), Length(max=255)])
    body = TextAreaField("Message", validators=[DataRequired(), Length(max=5000)])
    signature = TextAreaField(
        "Signature (facultatif, affichée après le bouton)",
        validators=[Optional(), Length(max=2000)],
    )
    test_email = StringField("Adresse de test", validators=[Optional(), Email(), Length(max=255)])
