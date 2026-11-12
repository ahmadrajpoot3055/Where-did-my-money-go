from decimal import Decimal
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, SelectField, DateField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

class SubscriptionForm(FlaskForm):
    name = StringField("Subscription / Service Name", validators=[DataRequired(), Length(max=120)])
    expected_amount = DecimalField("Expected Amount", places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    currency_code = SelectField("Currency", choices=[("PKR", "PKR"), ("USD", "USD"), ("EUR", "EUR"), ("GBP", "GBP")], default="PKR")
    frequency = SelectField("Billing Frequency", choices=[("Monthly", "Monthly"), ("Weekly", "Weekly"), ("Yearly", "Yearly"), ("Other", "Other")], default="Monthly")
    next_expected_date = DateField("Next Expected Date (Optional)", validators=[Optional()])
    submit = SubmitField("Save Subscription")

