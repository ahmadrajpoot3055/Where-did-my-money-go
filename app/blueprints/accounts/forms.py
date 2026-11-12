from decimal import Decimal
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DecimalField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange

class AccountForm(FlaskForm):
    name = StringField("Account Name", validators=[DataRequired(), Length(max=100)])
    account_type_id = SelectField("Account Type", coerce=int, validators=[DataRequired()])
    institution_name = StringField("Financial Institution (Optional)", validators=[Length(max=120)])
    currency_code = SelectField("Currency", choices=[("PKR", "PKR"), ("USD", "USD"), ("EUR", "EUR"), ("GBP", "GBP")], validators=[DataRequired()])
    opening_balance = DecimalField("Opening Balance", places=2, default=Decimal("0.00"), validators=[NumberRange(min=0, message="Opening balance must be non-negative")])
    submit = SubmitField("Save Account")

