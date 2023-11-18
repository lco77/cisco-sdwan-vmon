from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import (DataRequired, Email, EqualTo, Length, URL)


class UserForm(FlaskForm):
    username = StringField('username', validators=[DataRequired(message="Email is required"),
                                                   Email(message='Invalid e-mail address')])
    password = StringField('password', validators=[DataRequired(message="Old password is required"),
                                                   Length(8, 64, message='Password is too short')])


class PasswordForm(FlaskForm):
    password = StringField('password', validators=[DataRequired(message="Current password is required"),
                                                   Length(8, 64, message='Password is too short')])
    password_new1 = StringField('password_new1', validators=[DataRequired(message="New password is required"),
                                                             Length(8, 64, message='Password is too short')])
    password_new2 = StringField('password_new2', validators=[DataRequired(message="New password (repeat) is required"),
                                                             Length(8, 64, message='Password is too short'),
                                                             EqualTo('password_new1')])


class ServerForm(FlaskForm):
    server = StringField('server', validators=[DataRequired(message="URL is required"),
                                               URL(require_tld=True, message='URL is not valid')])
    username = StringField('username', validators=[DataRequired(message="Username is required")])
    password = StringField('password', validators=[DataRequired(message="Password is required"),
                                                   Length(8, 64, message='Password is too short')])
    description = StringField('description', validators=[DataRequired(message="Description is required")])
