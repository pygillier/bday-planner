from flask_wtf import FlaskForm
from wtforms import SelectMultipleField, StringField, TextAreaField, widgets
from wtforms.validators import Email, InputRequired, Length, Optional


class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class DetailsForm(FlaskForm):
    event_option_ids = MultiCheckboxField(
        "À quelles dates seriez-vous disponible ?", choices=[], coerce=int, validators=[Optional()]
    )
    email = StringField(
        "Adresse e-mail", validators=[Optional(), Email(), Length(max=255)]
    )
    dietary_notes = TextAreaField(
        "Allergies / régime particulier", validators=[Optional(), Length(max=2000)]
    )

    def require_email(self):
        """Called when the guest has no e-mail on file yet -- we now also
        reach guests by SMS, so we need to collect it at least once."""
        self.email.validators = [
            InputRequired(message="Merci de renseigner votre e-mail."),
            Email(),
            Length(max=255),
        ]

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
