from app import db
from flask_login import UserMixin
from datetime import datetime

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    social_id = db.Column(db.String(128), nullable=False, unique=True)
    nickname = db.Column(db.String(128), nullable=True)
    username = db.Column(db.String(128), nullable=False, unique=True)
    biography = db.Column(db.String(256), nullable=True)
    email = db.Column(db.String(256), nullable=True)
    profile_picture_url = db.Column(db.String(256), nullable=True)
    auth_provider = db.Column(db.String(256), nullable=False)
    approved_to_post = db.Column(db.Boolean, nullable=False)
    is_administrator = db.Column(db.Boolean, nullable=False)
    posts = db.relationship('Post', backref='users')

    def __repr__(self):
        return '<User %r>' % (self.nickname)

    @staticmethod
    def make_unique_nickname(nickname):
        if User.query.filter_by(nickname=nickname).first() is None:
            return nickname
        version = 1
        while True:
            new_nickname = nickname + str(version)
            if User.query.filter_by(nickname=nickname).first() is None:
                break
            version += 1
        return new_nickname

    def profile_pictures(self, size):
        if self.auth_provider == 'google':
            return self.profile_picture_url + "?sz=%s" % size
        elif self.auth_provider == 'facebook':
            return self.profile_picture_url + '?width=%s&height=%s' % (size, size)


class Post(db.Model, UserMixin):
    __tablename__='posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128))
    body = db.Column(db.String(10000))
    timestamp = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    images = db.relationship('Image', backref='posts')

    def summary(self, length):
        if self.body is None:
            return ""

        return (self.body[:length] + '...') if len(self.body) > length else self.body

    def __repr__(self):
        return '<Post %r with Images %r>' % (self.title, [i.url for i in self.images])

class Image(db.Model, UserMixin):
    __tablename__='images'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'))
    url = db.Column(db.String(128))

    def __repr__(self):
        return '<Image %r>' % (self.url)