from flask_wtf import Form
from wtforms import StringField, BooleanField, TextAreaField, TextField, SelectField, FileField
from wtforms.validators import DataRequired
import re, os

class PostForm(Form):
    title = StringField('title', validators=[DataRequired()])
    body = TextAreaField('body', validators=[DataRequired()])
    image = FileField(u'Image File', render_kw={'multiple': True})

class DeleteForm(Form):
    delete = StringField(validators=[DataRequired()])

class EditForm(Form):
    nickname = StringField('Nickname')
    biography = TextAreaField('About You')

class AdminForm(Form):
    approveemail = StringField('Email')
    disapproveemail = StringField('Email')