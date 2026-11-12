from decimal import Decimal
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DecimalField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional

class TransactionForm(FlaskForm):
    account_id = SelectField("Account", coerce=int, validators=[DataRequired()])
    transaction_date = DateField("Transaction Date", validators=[DataRequired()])
    description = StringField("Description", validators=[DataRequired(), Length(max=500)])
    amount = DecimalField("Amount", places=2, validators=[DataRequired(), NumberRange(min=0.01, message="Amount must be positive")])
    transaction_type_id = SelectField("Type", coerce=int, validators=[DataRequired()])
    category_id = SelectField("Category (Optional)", coerce=int, validators=[Optional()])
    reference = StringField("Reference / Check # (Optional)", validators=[Optional(), Length(max=120)])
    tags = StringField("Tags (comma-separated)", validators=[Optional(), Length(max=200)])
    note = TextAreaField("Notes", validators=[Optional()])
    submit = SubmitField("Save Transaction")

class TransactionSplitForm(FlaskForm):
    category_id = SelectField("Category", coerce=int, validators=[DataRequired()])
    amount = DecimalField("Split Amount", places=2, validators=[DataRequired(), NumberRange(min=0.01)])
    note = StringField("Split Note (Optional)", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Add Split")

class TransactionNoteForm(FlaskForm):
    body = TextAreaField("Note", validators=[DataRequired()])
    submit = SubmitField("Add Note")

