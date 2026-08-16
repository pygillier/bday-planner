from flask_wtf import FlaskForm
from wtforms import TextAreaField
from wtforms.validators import Length, Optional


class DetailsForm(FlaskForm):
    dietary_notes = TextAreaField(
        "Allergies / régime particulier", validators=[Optional(), Length(max=2000)]
    )
