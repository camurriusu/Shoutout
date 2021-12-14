from flask import Flask, render_template, session, redirect, request
from flask_table import Table, Col, LinkCol, DatetimeCol
from werkzeug.security import check_password_hash, generate_password_hash
from cs50 import SQL
from dotenv import load_dotenv
import os
import time
from functools import wraps

# Load .env file for app.secret_key
# Start database and Flask.
load_dotenv()
db = SQL("sqlite:///data.db")
app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = os.environ.get("SECRET_KEY")

# Contacts table class to be used for contacts.html
class Contacts(Table):
    classes = ["table table-striped"]
    thead_classes = ["table-dark"]
    id = Col('User ID', show=False)
    fname = Col('First name')
    sname = Col('Surname')
    username = Col('Username')
    bdate = Col('Birth Date')
    send = LinkCol('Send', 'sendto', url_kwargs=dict(username='username', id='id'))

# Messages table class to be used for messages.html
class Messages(Table):
    classes = ["table table-hover"]
    id = Col('User ID', show=False)
    sender = Col('Username')
    content = Col('Message')
    date = DatetimeCol('Sent at')

# Define decorator to stop logged out users from accessing certain pages
# that require you to be logged in.
def reqlogin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

# login.html
@app.route('/login', methods=["GET", "POST"])
def login():
    # Be sure session is empty before logging in.
    session.clear()
    if request.method == "POST":
        # Return users that have the same username that was entered.
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("uname"))
        # If rows is empty or password incorrect, login fails.
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return render_template("login.html", err=True)
        # If login succeeds start new session with user's id.
        session["user_id"] = rows[0]["id"]
        session["username"] = rows[0]["username"]
        
        return redirect("/")
    else:
        return render_template("login.html", err=False)

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        uname = request.form.get("uname")
        fname = request.form.get("fname")
        sname = request.form.get("sname")
        pw = request.form.get("password")
        
        # Get users with username matching with uname.
        row = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("uname"))
        # If there is someone with the that username, register fails.
        if len(row) != 0:
            return render_template("register.html", err=True)
        # Check if username and password meet requirements (see alert variable).
        if len(fname) <= 1:
            return render_template("register.html", alert="First name must have more than 1 letters.")
        elif len(sname) <= 2:
            return render_template("register.html", alert="Second name must have more than 2 letters.")
        elif not pw == request.form.get("confirmation"):
            return render_template("register.html", alert="Passwords do not match.")
        elif len(uname) <= 4:
            return render_template("register.html", alert="Username must be at least 5 letters long.")
        elif len(pw) < 8 or any(s.isdigit() for s in pw) == False or any(s.isupper() for s in pw) == False:
            return render_template("register.html", alert="Password must have at least 8 characters, one number, and one capital letter.")
        db.execute("INSERT INTO users (fname, sname, bdate, username, hash) VALUES(?, ?, ?, ?, ?)", fname, sname, request.form.get("age"), uname,
        generate_password_hash(pw))

        return redirect("/")
    else:
        return render_template("register.html", err=False)

# Logs user out by clearing their session.
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# contacts.html
@app.route('/', methods=["GET", "POST"])
@reqlogin
def contacts():
    # Get all users (not including logged in user) to then turn them into a table using Contacts class.
    qry = db.execute("SELECT * FROM users WHERE id != ? ORDER BY fname ASC;", session["user_id"])
    contacts = Contacts(qry)
    return render_template('contacts.html', table=contacts)

# Sending message to specific user.
@app.route('/sendto/<string:username><int:id>', methods=['GET', 'POST'])
@reqlogin
def sendto(username, id):
    if request.method == "POST":
        # Get message written.
        content = request.form.get("msg")
        # Send it.
        db.execute("INSERT INTO messages (sender, receiver_id, content, date) VALUES(?, ?, ?, ?)", session["username"], id, content, time.time())
        
        return render_template("/sendto.html", user=username, alert="Message sent!")
    else:
        return render_template("/sendto.html", user=username)
    
@app.route("/send", methods=["GET", "POST"])
@reqlogin
def send():
    if request.method == "POST":
        # Get id of user who will receive the message
        receiver = db.execute("SELECT id FROM users WHERE username = ?", request.form.get("uname"))
        # Get content of the message and send it
        content = request.form.get("msg")
        db.execute("INSERT INTO messages (sender, receiver_id, content, date) VALUES(?, ?, ?, ?)", session["username"], receiver[0]['id'], content, time.time())
        
        return render_template("/send.html", alert="Message sent!")
    else:
        return render_template("/send.html")

@app.route("/messages", methods=["GET", "POST"])
@reqlogin
def messages():
    if request.method == "POST":
        # Get users who have received/sent a message from/to you before.
        users = db.execute("SELECT username FROM users WHERE id IN (SELECT receiver_id FROM messages WHERE sender = ?) OR (SELECT sender FROM messages WHERE receiver_id = ?)", session["username"], session["username"])
        # Username chosen.
        username = request.form.get("select")
        # If no username was chosen from menu, return a None table.
        if username == 'Select a user':
            return render_template("/messages.html", table=None, users=users)
        # Get id of chosen user.
        userid = db.execute("SELECT id FROM users WHERE username = ?", username)
        # Get messages that you sent and received from them, and turn those values into a table to show using Messages class.
        qry = db.execute("SELECT * FROM messages WHERE (receiver_id = ? AND sender = ?) OR (receiver_id = ? AND sender = ?) ORDER BY date DESC", userid[0]['id'], session["username"], session["user_id"], username)
        messages = Messages(qry)
        
        return render_template("/messages.html", table=messages, users=users)
    else:
        # Get users who have received/sent a message from/to you before.
        users = db.execute("SELECT username FROM users WHERE id != ?", session["user_id"])
        
        return render_template("/messages.html", table=None, users=users)