import os
from flask import Flask, session
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_sitemap import Sitemap


app = Flask(__name__)
ext = Sitemap(app=app)

bcrypt = Bcrypt()
# Check for environment variable
if not os.environ["DATABASE_URL"]:
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ['EMAIL_USER']
app.config['MAIL_PASSWORD'] = os.environ['EMAIL_PASS']
mail = Mail(app)

Session(app)

# Set up database


engine = create_engine(os.environ['DATABASE_URL'])

db = scoped_session(sessionmaker(bind=engine))
bcrypt.init_app(app)


from app.bookapp import routes

@ext.register_generator
def index():
    yield 'index', {}
