from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime
import secrets
from flask_migrate import Migrate

site = SQLAlchemy()

class User(site.Model, UserMixin ):
    id = site.Column(site.Integer, primary_key=True)
    username = site.Column(site.String(20), unique=True, nullable=False)
    email = site.Column(site.String(120), unique=True, nullable=False)
    image_file = site.Column(site.String(20), nullable=False, default='default.jpg')
    password = site.Column(site.String(60), nullable=False)
    bio = site.Column(site.Text, nullable=True, default='')
    avatar = site.Column(site.String(255), nullable=False, default='default_avatar.png')
    two_factor_enabled = site.Column(site.Boolean, default=False)
    two_factor_secret = site.Column(site.String(32), nullable=True)
    theme = site.Column(site.String(50), default="default")
    custom_accent = site.Column(site.String(20), nullable=True)
    custom_bg = site.Column(site.String(20), nullable=True)
    custom_container = site.Column(site.String(20), nullable=True)
    role = site.Column(site.String(20), default="user")
    is_blocked = site.Column(site.Boolean, default=False)
    created_at = site.Column(site.DateTime, default=datetime.utcnow)




    # Flask-Login
    def get_id(self):
        return str(self.id)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class File(site.Model):
    id = site.Column(site.Integer, primary_key=True)
    storage_filename = site.Column(site.String(255), nullable=True)
    filename = site.Column(site.String(255), nullable=False) 
    upload_time = site.Column(site.DateTime, nullable=False, default=datetime.utcnow)
    user_id = site.Column(site.Integer, site.ForeignKey('user.id'), nullable=False)
    batch_id = site.Column(site.String(36), nullable=True)
    file_data = site.Column(site.LargeBinary, nullable=True)
    description = site.Column(site.Text, nullable=True)
    is_public = site.Column(site.Boolean, default=False)
    share_token = site.Column(site.String(64), nullable=True)
    
    user = site.relationship('User', backref=site.backref('files', lazy=True))

