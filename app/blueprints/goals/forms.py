from decimal import Decimal
from flask_wtf import FlaskForm
from wtforms import StringField, DecimalField, DateField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

class SavingsGoalForm(FlaskForm):
    name = StringField("Goal Name", validators=[DataRequired(), Length(max=100)])
    target_amount = DecimalField("Target Amount", places=2, validators=[DataRequired(), NumberRange(min=1.00)])
    target_date = DateField("Target Completion Date (Optional)", validators=[Optional()])
    currency_code = SelectField("Currency", choices=[("PKR", "PKR"), ("USD", "USD"), ("EUR", "EUR"), ("GBP", "GBP")], default="PKR")
    submit = SubmitField("Create Savings Goal")

class SavingsContributionForm(FlaskForm):
    amount = DecimalField("Contribution Amount", places=2, validators=[DataRequired(), NumberRange(min=1.00)])
    contribution_date = DateField("Date", validators=[DataRequired()])
    note = StringField("Note (Optional)", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Add Contribution")

