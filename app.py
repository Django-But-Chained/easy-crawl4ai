import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", os.urandom(24).hex())

# configure the database - make sure we have DATABASE_URL from environment
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    # If no database URL is provided, use a default SQLite database
    print("WARNING: DATABASE_URL not set. Using SQLite database.")
    database_url = "sqlite:///crawl4ai.db"

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# initialize the app with the extension
db.init_app(app)

with app.app_context():
    # Import the models here or their tables won't be created
    import models  # noqa: F401

    db.create_all()