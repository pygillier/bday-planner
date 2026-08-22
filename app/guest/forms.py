from flask_wtf import FlaskForm
from wtforms import SelectMultipleField, TextAreaField, widgets
from wtforms.validators import InputRequired, Length, Optional


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class DetailsForm(FlaskForm):
    event_option_ids = MultiCheckboxField(
        "À quelles dates seriez-vous disponible ?", choices=[], coerce=int, validators=[Optional()]
    )
    dietary_notes = TextAreaField(
        "Allergies / régime particulier", validators=[Optional(), Length(max=2000)]
    )

    def set_event_options(self, options):
        """Populate choices from the admin-configured dates and make the
        field required only when there's actually something to choose."""
        self.event_option_ids.choices = [(option.id, option.display_text) for option in options]
        if options:
            self.event_option_ids.validators = [
                InputRequired(message="Merci de choisir au moins une date.")
            ]
        else:
            self.event_option_ids.validators = [Optional()]
