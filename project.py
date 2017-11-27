from flask import Flask, render_template, url_for, redirect, request, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
import app.connect as connect
import config
import datetime


app = Flask(__name__)
app.config.from_object(config)
app.secret_key = '\xdaW\x9b4\x8a\x00i\xfb\xaa\x8aW\xa2\xed\x81N\x02\xb9\x00\xbb\xee\xd2\x1c\x12\xc9'
db = SQLAlchemy(app)


# user info table
class User(db.Model):
    __tablename__ = 'user'
    username = db.Column(db.String(10), nullable=False)
    password = db.Column(db.String(16), nullable=False)
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(50), nullable=False)
    avatar = db.Column(db.String(300))
    createtime = db.Column(db.DateTime, nullable=False)
    info = db.Column(db.Text)


# system set table
class Sys(db.Model):
    __tablename__ = 'system_set'
    ip = db.Column(db.String(15), nullable=False, primary_key=True)
    port = db.Column(db.String(5), nullable=False)
    username = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(20), nullable=False)


db.create_all()


@app.route('/import/')
def import_img():
    request_type = request.args.get('type')
    if request_type is 'local':
        pass
    else:
        pass
    return render_template('import-port.html')


# login function
@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if 'username' not in session:
            return render_template('page-login.html')
        elif 'lock_stat' in session:
            return redirect(url_for('lock'))
        else:
            return redirect(url_for('index'))
    else:
        user = User.query.filter(User.username == request.form['username']).first()
        if user is not None:
            if request.form['password'] != user.password:
                error = 'username or password error'
            else:
                session['username'] = user.username
                flash('login sucess')
                return redirect(url_for('index'))
        else:
            error = 'user is not found'
    flash(error)
    return redirect(url_for('login'))


# logout function
@app.route('/logout/')
def logout():
    if 'username' in session:
        session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/search/')
def search():
    pass


@app.route('/settings/', methods=['GET', 'POST'])
def settings():
    pass


@app.route('/lockscreen/', methods=['GET', 'POST'])
def lock():
    if request.method == 'GET':
        session['lock_stat'] = True
        if 'username' in session:
            user = User.query.filter(User.username == session['username']).first()
            context = {
                'username': user.username,
                'avatar': user.avatar
            }
            if context.get('avatar') is None:
                context.pop('avatar')
            return render_template('page-lockscreen.html', **context)
        else:
            return redirect(url_for('login'))
    else:
        user = User.query.filter(User.username == session['username']).first()
        password = request.form['password']
        if user.password == password:
            session.pop('lock_stat')
            return redirect(url_for('index'))
        else:
            return redirect(url_for('lock'))


@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    elif 'lock_stat' in session:
        return  redirect(url_for('lock'))
    user = User.query.filter(User.username == session['username']).first()
    flush_time = datetime.datetime.strftime(datetime.datetime.now(), '%b %d, %Y  %I:%M %p')
    context = {
        'username': user.username,
        'avatar': user.avatar,
        'user_id': user.user_id,
        'flush_time': flush_time
    }
    if context.get('avatar') is None:
        context.pop('avatar')
    return render_template('index.html', **context)


if __name__ == '__main__':
    app.run(debug=True)
