from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, BooleanField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
from app.models.user import User

class RegisterForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email Address", validators=[DataRequired(), Email(), Length(max=255)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6, max=128)])
    confirm_password = PasswordField("Confirm Password", validators=[DataRequired(), EqualTo("password", message="Passwords must match")])
    submit = SubmitField("Create Account")

    def validate_email(self, field):
        normalized_email = field.data.strip().lower()
        if User.query.filter(User.email.ilike(normalized_email)).first():
            raise ValidationError("An account with this email address already exists.")

class LoginForm(FlaskForm):
    email = StringField("Email Address", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")

class ProfileForm(FlaskForm):
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    currency_code = SelectField("Default Currency", choices=[("PKR", "PKR (Pakistani Rupee)"), ("USD", "USD (US Dollar)"), ("EUR", "EUR (Euro)"), ("GBP", "GBP (British Pound)")], validators=[DataRequired()])
    timezone = SelectField("Timezone", choices=[("Asia/Karachi", "Asia/Karachi (PKT)"), ("UTC", "UTC"), ("America/New_York", "America/New_York (EST)")], validators=[DataRequired()])
    theme = SelectField("Interface Theme", choices=[("light", "Light Mode"), ("dark", "Dark Mode")], validators=[DataRequired()])
    submit = SubmitField("Update Profile")

