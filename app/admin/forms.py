from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import StringField
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
