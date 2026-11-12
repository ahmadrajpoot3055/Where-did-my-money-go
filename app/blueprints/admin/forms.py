from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange

class AdminCategoryForm(FlaskForm):
    name = StringField("Category Name", validators=[DataRequired(), Length(max=80)])
    kind = SelectField("Kind", choices=[("Expense", "Expense"), ("Income", "Income"), ("Both", "Both")], default="Expense")
    submit = SubmitField("Save Category")

class AdminSubcategoryForm(FlaskForm):
    category_id = SelectField("Parent Category", coerce=int, validators=[DataRequired()])
    name = StringField("Subcategory Name", validators=[DataRequired(), Length(max=80)])
    submit = SubmitField("Add Subcategory")

class AdminMerchantForm(FlaskForm):
    name = StringField("Canonical Merchant Name", validators=[DataRequired(), Length(max=120)])
    default_category_id = SelectField("Default Category (Optional)", coerce=int, validators=[Optional()])
    website = StringField("Website (Optional)", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Save Merchant")

class AdminMerchantAliasForm(FlaskForm):
    merchant_id = SelectField("Merchant", coerce=int, validators=[DataRequired()])
    alias_text = StringField("Statement Alias Text", validators=[DataRequired(), Length(max=180)])
    submit = SubmitField("Add Merchant Alias")

class AdminCategoryRuleForm(FlaskForm):
    category_id = SelectField("Target Category", coerce=int, validators=[DataRequired()])
    pattern = StringField("Matching Pattern / Keyword", validators=[DataRequired(), Length(max=200)])
    match_type = SelectField("Match Type", choices=[("Contains", "Contains"), ("Exact", "Exact"), ("Regex", "Regex")], default="Contains")
    priority = IntegerField("Priority (Higher = Evaluated First)", default=10, validators=[DataRequired(), NumberRange(min=1, max=100)])
    submit = SubmitField("Add Rule")

