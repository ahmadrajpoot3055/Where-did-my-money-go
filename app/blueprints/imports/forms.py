from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Optional

class StatementUploadForm(FlaskForm):
    account_id = SelectField("Target Account", coerce=int, validators=[DataRequired()])
    file = FileField("Bank Statement File (.csv, .xlsx)", validators=[
        FileRequired(),
        FileAllowed(["csv", "xlsx", "xls"], "Only CSV and Excel (.xlsx) files are permitted")
    ])
    submit = SubmitField("Upload & Continue")

class ColumnMappingForm(FlaskForm):
    date_column = SelectField("Transaction Date Column", validators=[DataRequired()])
    description_column = SelectField("Description Column", validators=[DataRequired()])
    mapping_type = SelectField("Amount Format", choices=[("single", "Single Amount Column (positive/negative)"), ("debit_credit", "Separate Debit and Credit Columns")], default="single")
    amount_column = SelectField("Amount Column", validators=[Optional()])
    debit_column = SelectField("Debit / Expense Column", validators=[Optional()])
    credit_column = SelectField("Credit / Income Column", validators=[Optional()])
    date_format = StringField("Date Format (e.g. %Y-%m-%d, %d/%m/%Y, or leave blank to auto-detect)", validators=[Optional()])
    submit = SubmitField("Process & Preview")

