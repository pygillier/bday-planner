from flask_wtf import FlaskForm
from wtforms import RadioField, TextAreaField
from wtforms.validators import InputRequired, Length, Optional


class DetailsForm(FlaskForm):
    event_option_id = RadioField(
        "À quelle date viendrez-vous ?", choices=[], coerce=int, validators=[Optional()]
    )
    dietary_notes = TextAreaField(
        "Allergies / régime particulier", validators=[Optional(), Length(max=2000)]
    )

    def set_event_options(self, options):
        """Populate choices from the admin-configured dates and make the
        field required only when there's actually something to choose."""
        self.event_option_id.choices = [(option.id, option.display_text) for option in options]
        if options:
            self.event_option_id.validators = [InputRequired(message="Merci de choisir une date.")]
        else:
            self.event_option_id.validators = [Optional()]
