from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
import os

application = Flask(__name__)
app = application
app.config.from_object('config')

db = SQLAlchemy(app)
lm = LoginManager(app)

from app import views, models
from app.models import User

@lm.user_loader
def load_user(id):
    return User.query.get(int(id))