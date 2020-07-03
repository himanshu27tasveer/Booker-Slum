from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField,TextAreaField
from wtforms.validators import DataRequired, EqualTo, Length, Email, ValidationError
from app.bookapp import db


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])


class RegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(),Length(min=2, max=20)])
    username = StringField('Username', validators=[DataRequired(),Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(),Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign up')

    def validate_username(self,username):
        user = db.execute("SELECT * FROM users WHERE username = :username",{"username":username.data}).fetchone()
        if user:
            raise ValidationError('Username is already taken. Please choose a different one.')
    def validate_email(self, email):
        user = db.execute("SELECT * FROM users WHERE email = :email",{"email":email.data}).fetchone()
        if user:
            raise ValidationError('Email is already taken. Please choose a different one.')



class RequestResetForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

    def validate_email(self, email):
        user = db.execute("SELECT * FROM users WHERE email = :email",{"email":email.data}).fetchone()
        if user is None:
            raise ValidationError('Email does not exist. Please register first.')


class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')



class ReviewForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content',validators=[DataRequired()])
    submit = SubmitField('Submit')