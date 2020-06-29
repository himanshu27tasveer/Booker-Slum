import os, json
import secrets
import requests
from flask import render_template, url_for, flash, redirect, request, abort, session, jsonify
from app.bookapp import app, db, bcrypt, mail, ext
from flask_mail import Message
from app.bookapp.forms import RequestResetForm, ResetPasswordForm, ReviewForm
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
import pytz
from datetime import datetime
from wtforms.validators import ValidationError

tz_India = pytz.timezone('Asia/Kolkata')


from flask import redirect, render_template, request, session
from functools import wraps

""" Decorator for Login Required """


def login_required(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if session.get("user_id") is None:
			flash('You need to Login First', 'danger')
			return redirect(url_for('login'))
		return f(*args, **kwargs)
	return decorated_function


def validate_username(username):
		user = db.execute("SELECT * FROM users WHERE username = :username",{"username":username}).fetchone()
		if user:
			raise ValidationError('Username is already taken. Please choose a different one.')
		else:
			return True
def validate_email(email):
	user = db.execute("SELECT * FROM users WHERE email = :email",{"email":email}).fetchone()
	if user:
		raise ValidationError('Email is already taken. Please choose a different one.')
	else:
		return True



@app.route('/')
@app.route('/home')
def home():
	return render_template("home.html", title='Booker-Slum')


@ext.register_generator
def index():
    yield 'home', {}



@app.route("/register", methods=['GET','POST'])
def register():
	if request.method == 'POST':
		name = request.form.get("name")
		username = request.form.get("username")
		email = request.form.get("email")
		password = request.form.get("password")
		confpassword = request.form.get("confpassword")
		if password == confpassword:
			if validate_username(username) and validate_email(email):
				hashed_pass = bcrypt.generate_password_hash(password).decode()
				user = db.execute("INSERT INTO users (name, username, email, password) VALUES (:name ,:username, :email, :password)", {"name":name,"username":username, "email":email, "password":hashed_pass})
				db.commit()
				flash('Account has been created, You can now login', 'success')
				return redirect( url_for('login') )
		else:
			flash('Password do not match', 'danger')
	return render_template("register.html", title='Sign Up')


@app.route("/login", methods=['GET','POST'])
def login():
	session.clear()
	if request.method == 'POST':
		email = request.form.get("email")
		password = request.form.get("password")
		user = db.execute("SELECT * FROM users WHERE email = :email",{"email":email}).fetchone()
		if user and bcrypt.check_password_hash(user.password, password):
			next_page = request.args.get('next') 
			session["user_id"] = user.id
			session["user_name"] = user.username
			flash('Successfully Logged in', 'success')
			return redirect(url_for('home'))
		else:
			flash("Login Failed", 'danger')
	return render_template("login.html", title='Login')



@app.route("/logout", methods=['GET','POST'])
@login_required
def logout():
	session.clear()
	flash('Successfully logged out', 'success')
	return redirect("/home")


@app.route("/account")
@login_required
def account():
	user_id = session.get('user_id', None)
	user = db.execute("SELECT * FROM users WHERE id = :id",{"id":user_id}).fetchone()
	response = db.execute("SELECT * FROM cart WHERE user_id = :id",{"id":user_id})
	books = response.fetchall()
	username = user.username
	email = user.email
	return render_template("account.html", email=email, username=username, books=books, num = response.rowcount, title='Account')



def get_reset_token(id, expires_sec=1800):
		s = Serializer(app.config['SECRET_KEY'], expires_sec)
		return s.dumps({'user_id': id}).decode('utf-8')


def verify_reset_token(token):
	s = Serializer(app.config['SECRET_KEY'])
	try:
		user_id = s.loads(token)['user_id']
	except:
		return None
	return user_id




def send_reset_email(user_id,email):
	token = get_reset_token(user_id)
	msg = Message('Password Reset Request',
				  sender='himanshu27.stu@gmail.com',
				  recipients=[email])
	msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}
If you did not make this request then simply ignore this email and no changes will be made.
'''
	mail.send(msg)




@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
	form = RequestResetForm()
	if form.validate_on_submit():
		user =  db.execute("SELECT * FROM users WHERE email = :email",{"email":form.email.data}).fetchone()
		email = user.email
		user_id = user.id
		send_reset_email(user_id,email)
		message = 'An email has been sent with instructions to reset your password.'
		return render_template('reset.html', title='Reset Password', message=message)
	return render_template('request_reset.html', title='Reset Password', form=form)


@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
	form = ResetPasswordForm()
	user_id = verify_reset_token(token)
	if user_id is None:
		flash('That is an invalid or expired token', 'warning')
		return redirect(url_for('reset_request'))
	if form.validate_on_submit():
		hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
		db.execute("UPDATE users SET password = :password WHERE id=:id",{"password":hashed_password, "id":user_id})
		db.commit()
		message = 'Your password has been updated! You are now able to log in'
		return render_template('reset.html', title='Reset Password', message=message)
	return render_template('reset_password.html', title='Reset Password', form=form)


	

@app.route('/search', methods=['GET'])
@login_required
def search():
	if not request.args.get("book"):
		flash("you must provide a book.", 'danger')
		return render_template("home.html")
	query = "%" + request.args.get("book") + "%"
	query = query.title()
	
	rows = db.execute("SELECT id, isbn, title, author, year FROM books WHERE \
						isbn LIKE :query OR \
						title LIKE :query OR \
						author LIKE :query LIMIT 15",
						{"query": query})
	
	if rows.rowcount == 0:
		flash("we can't find books with that description.", 'danger')
		return render_template("home.html", title='Booker-Slum')
	books = rows.fetchall()
	return render_template("query.html", books=books, results=rows.rowcount, title=request.args.get("book"))

	



@app.route("/book_info/<int:id>", methods=['GET','POST'])
@login_required
def book_info(id):
	form = ReviewForm()
	book = db.execute("SELECT isbn, title, author, year FROM books WHERE id=:id",{"id":id}).fetchone()
	bookisbn = book.isbn
	book_id = id
	try:
		user_id = session['user_id']
	except KeyError :
		flash('Please Login again', 'danger')
		return redirect(url_for('home'))
	if request.method == 'POST':
		booktitle = request.form.get('title')
		bookrating = request.form.get("stars")
		bookrating = int(bookrating)
		bookreview = request.form.get("review")
		db.execute("INSERT INTO reviews (review, user_id, book_id, rating, title, time) VALUES (:review, :user_id, :book_id, :rating, :title, :time)", 
								{"isbn":bookisbn, "review":bookreview, "user_id":user_id, "book_id":book_id, "rating":bookrating, "title":booktitle, "time":datetime.now(tz_India)})
		db.commit()
		return redirect("/book_info/" + str(book_id))
	else:
		try:
			res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": os.environ['GREADS_API'], "isbns": bookisbn})
			greads = res.json()
			greads = greads['books'][0]
			response = db.execute("SELECT users.username, review, rating, time FROM users INNER JOIN reviews ON users.id = reviews.user_id WHERE book_id = :book ORDER BY time", {"book": book_id})

			results = response.fetchall()

			return render_template("book_info.html", book=book, results=results,greads=greads, form=form, num=response.rowcount, title=book.title)
		except requests.exceptions.SSLError:
			flash('Connection Refused. Please wait for sometime', 'danger')
			return redirect(url_for('home'))
			

@app.route('/add_to_cart/<int:id>', methods=['POST'])
@login_required
def cart(id):
	addbook = request.form.get('add')
	res = db.execute("SELECT * FROM cart WHERE isbn = :isbn",{"isbn":addbook})
	if res.rowcount==0:
		if addbook:
			curr = db.execute("SELECT * FROM books WHERE isbn=:isbn", {"isbn":addbook}).fetchone()
			db.execute("INSERT INTO cart (title, book_id, user_id, isbn) VALUES (:title, :book_id, :user_id, :isbn)",{"title":curr.title, "book_id":curr.id, "user_id":id, "isbn":curr.isbn})
			db.commit()
			flash('Book is Added. You can check in your cart.', 'info')
			return redirect(request.referrer)
	else:
		flash('This book is already in your cart', 'info')
		return redirect(request.referrer)




@app.route("/api/<isbn>", methods=['GET'])
@login_required
def api_call(isbn):
	isbn = str(isbn)
	row = db.execute("SELECT books.title, author, year, isbn, COUNT(reviews.id) as review_count, AVG(reviews.rating) as average_score FROM books INNER JOIN reviews ON books.id = reviews.book_id WHERE isbn = :isbn GROUP BY books.title, author, year, isbn", {"isbn": isbn})

	if row.rowcount == 0:
		row_nxt = db.execute("SELECT id, title, author, year, isbn FROM books WHERE isbn = :isbn", {"isbn": isbn})
		if row_nxt.rowcount == 0:
			return jsonify({"Error": "Invalid book ISBN"}), 422
		else:
			book = row_nxt.fetchone()
			result = {
				"title": book.title,
				"author": book.author,
				"year": book.year,
				"isbn": book.isbn,
				"review_count": 0,
				"average_score": 0
			}
			return jsonify(result)

	result = {
				"title": book.title,
				"author": book.author,
				"year": book.year,
				"isbn": book.isbn,
				"review_count": book.ratings_count,
				"average_score": book.rating
			}
	result['average_score'] = float('%.2f'%(result['average_score']))

	return jsonify(result)
