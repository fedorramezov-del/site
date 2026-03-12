import os
import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = "Very_difficult_secret_key)))))))))))"

    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "site.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAX_CONTENT_LENGTH = 500 * 1024 * 1024   # 500MB

    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static/uploads/files")
    AVATAR_FOLDER = os.path.join(BASE_DIR, "static/uploads/avatars")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_DOMAIN = False

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None