from decimal import Decimal
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DecimalField, DateField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange

class BudgetForm(FlaskForm):
    name = StringField("Budget Name", validators=[DataRequired(), Length(max=100)])
    period_type = SelectField("Period Type", choices=[("Monthly", "Monthly"), ("Weekly", "Weekly"), ("Custom", "Custom")], default="Monthly")
    start_date = DateField("Start Date", validators=[DataRequired()])
    end_date = DateField("End Date", validators=[DataRequired()])
    currency_code = SelectField("Currency", choices=[("PKR", "PKR"), ("USD", "USD"), ("EUR", "EUR"), ("GBP", "GBP")], default="PKR")
    submit = SubmitField("Create Budget")

class BudgetItemForm(FlaskForm):
    category_id = SelectField("Category", coerce=int, validators=[DataRequired()])
    limit_amount = DecimalField("Expense Limit", places=2, validators=[DataRequired(), NumberRange(min=1.00)])
    warning_percent = DecimalField("Warning Alert Threshold (%)", places=2, default=Decimal("80.00"), validators=[NumberRange(min=10, max=100)])
    submit = SubmitField("Add Category Limit")

