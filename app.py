from flask import Flask, render_template, session, redirect, request
from flask_table import Table, Col, LinkCol, DatetimeCol, ButtonCol
from werkzeug.security import check_password_hash, generate_password_hash
from cs50 import SQL
from dotenv import load_dotenv
import os
import time
from functools import wraps

load_dotenv()
db = SQL("sqlite:///data.db")
app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
app.secret_key = os.environ.get("SECRET_KEY")

class Contacts(Table):
    classes = ["table table-striped"]
    thead_classes = ["table-dark"]
    id = Col('User ID', show=False)
    fname = Col('First name')
    sname = Col('Surname')
    username = Col('Username')
    bdate = Col('Birth Date')
    send = LinkCol('Send', 'sendto', url_kwargs=dict(username='username', id='id'))

class Messages(Table):
    classes = ["table table-hover"]
    id = Col('User ID', show=False)
    sender = Col('Username')
    content = Col('Message')
    date = DatetimeCol('Sent at')

def reqlogin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=["GET", "POST"])
def login():
    session.clear()
    err = False
    if request.method == "POST":
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("uname"))
        
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            err = True
        
        if err:
            return render_template("login.html", err=err)

        session["user_id"] = rows[0]["id"]

        return redirect("/")
    else:
        return render_template("login.html", err=err)

@app.route('/register', methods=["GET", "POST"])
def register():
    err = False
    if request.method == "POST":
        uname = request.form.get("uname")
        fname = request.form.get("fname")
        sname = request.form.get("sname")
        pw = request.form.get("password")
        
        row = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("uname"))

        if len(row) != 0:
            err = True

        if err:
            return render_template("register.html", err=err)

        if len(fname) <= 1:
            return render_template("register.html", alert="First name must have more than 1 letters.")
        
        if len(sname) <= 2:
            return render_template("register.html", alert="Second name must have more than 2 letters.")
        
        if not pw == request.form.get("confirmation"):
            return render_template("register.html", alert="Passwords do not match.")
        
        if len(uname) <= 4:
            return render_template("register.html", alert="Username must be at least 5 letters long.")

        if len(pw) < 8 or any(s.isdigit() for s in pw) == False or any(s.isupper() for s in pw) == False:
            return render_template("register.html", alert="Password must have at least 8 characters, one number, and one capital letter.")
        db.execute("INSERT INTO users (fname, sname, bdate, username, hash) VALUES(?, ?, ?, ?, ?)", fname, sname, request.form.get("age"), uname,
        generate_password_hash(pw))

        return redirect("/")
    else:
        return render_template("register.html", err=err)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route('/', methods=["GET", "POST"])
@reqlogin
def contacts():
    qry = db.execute("SELECT * FROM users WHERE id != ? ORDER BY fname ASC;", session["user_id"])
    contacts = Contacts(qry)
    return render_template('contacts.html', table=contacts)

@app.route('/sendto/<string:username><int:id>', methods=['GET', 'POST'])
@reqlogin
def sendto(username, id):
    if request.method == "POST":
        user = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
        content = request.form.get("msg")
        db.execute("INSERT INTO messages (sender, receiver_id, content, date) VALUES(?, ?, ?, ?)", user[0]['username'], id, content, time.time())
        
        return render_template("/sendto.html", user=username, alert="Message sent!")
    else:
        return render_template("/sendto.html", user=username)
    
@app.route("/send", methods=["GET", "POST"])
@reqlogin
def send():
    if request.method == "POST":
        user = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
        receiver = db.execute("SELECT id FROM users WHERE username = ?", request.form.get("uname"))
        content = request.form.get("msg")
        db.execute("INSERT INTO messages (sender, receiver_id, content, date) VALUES(?, ?, ?, ?)", user[0]['username'], receiver[0]['id'], content, time.time())
        
        return render_template("/send.html", alert="Message sent!")
    else:
        return render_template("/send.html")

@app.route("/messages", methods=["GET", "POST"])
@reqlogin
def messages():
    if request.method == "POST":
        loggedusername = db.execute("SELECT username FROM users WHERE id = ?", session["user_id"])
        users = db.execute("SELECT username FROM users WHERE id IN (SELECT receiver_id FROM messages WHERE sender = ?) OR (SELECT sender FROM messages WHERE receiver_id = ?)", loggedusername[0]['username'], loggedusername[0]['username'])
        username = request.form.get("select")
        if username == 'Select a user':
            return render_template("/messages.html", table=None, users=users)
        
        userid = db.execute("SELECT id FROM users WHERE username = ?", username)
        qry = db.execute("SELECT * FROM messages WHERE (receiver_id = ? AND sender = ?) OR (receiver_id = ? AND sender = ?) ORDER BY date DESC", userid[0]['id'], loggedusername[0]['username'], session["user_id"], username)
        messages = Messages(qry)
        
        return render_template("/messages.html", table=messages, users=users)
    else:
        users = db.execute("SELECT username FROM users WHERE id != ?", session["user_id"])
        
        return render_template("/messages.html", table=None, users=users)