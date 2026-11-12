from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length

class ReportForm(FlaskForm):
    title = StringField("Report Title", default="Monthly Financial Health Report", validators=[DataRequired(), Length(max=150)])
    period_start = DateField("Start Date", validators=[DataRequired()])
    period_end = DateField("End Date", validators=[DataRequired()])
    format = SelectField("Export Format", choices=[("CSV", "CSV Spreadsheet"), ("HTML", "Web View (HTML)")], default="CSV")
    currency_code = SelectField("Currency", choices=[("PKR", "PKR"), ("USD", "USD"), ("EUR", "EUR"), ("GBP", "GBP")], default="PKR")
    submit = SubmitField("Generate Report")

