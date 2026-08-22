from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import DateTimeLocalField, StringField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, Optional


class GuestForm(FlaskForm):
    first_name = StringField("Prénom", validators=[DataRequired(), Length(max=120)])
    last_name = StringField("Nom", validators=[DataRequired(), Length(max=120)])
    email = StringField("E-mail", validators=[Optional(), Email(), Length(max=255)])
    phone = StringField("Téléphone", validators=[Optional(), Length(max=50)])


class ImportForm(FlaskForm):
    csv_file = FileField(
        "Fichier CSV",
        validators=[FileRequired(), FileAllowed(["csv"], "Fichier CSV uniquement.")],
    )


class EventOptionForm(FlaskForm):
    label = StringField(
        "Intitulé (facultatif)", validators=[Optional(), Length(max=255)]
    )
    starts_at = DateTimeLocalField(
        "Date et heure", format="%Y-%m-%dT%H:%M", validators=[DataRequired()]
    )


class EmailTemplateForm(FlaskForm):
    subject = StringField("Objet de l'e-mail", validators=[DataRequired(), Length(max=255)])
    body = TextAreaField("Message", validators=[DataRequired(), Length(max=5000)])
    test_email = StringField(
        "Adresse de test", validators=[Optional(), Email(), Length(max=255)]
    )
