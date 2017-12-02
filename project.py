from flask import Flask, render_template, url_for, redirect, request, session, flash,send_file
from flask_sqlalchemy import SQLAlchemy
import config
import datetime
from app.tool import ConnectNode
connect = None

app = Flask(__name__)
app.config.from_object(config)
db = SQLAlchemy(app)


# user info table
class User(db.Model):
    __tablename__ = 'user'
    username = db.Column(db.String(10), nullable=False, primary_key=True)
    password = db.Column(db.String(16), nullable=False)
    user_id = db.Column(db.Integer, autoincrement=True)
    email = db.Column(db.String(50), nullable=False)
    avatar = db.Column(db.String(300))
    createtime = db.Column(db.DateTime, nullable=False)
    role = db.Column(db.String(10), nullable=False)
    info = db.Column(db.Text)


# node set table
class Sys(db.Model):
    __tablename__ = 'sys_set'
    image_dir = db.Column(db.String(50), nullable=False, primary_key=True)


# node set table
class Node(db.Model):
    __tablename__ = 'node_set'
    ip = db.Column(db.String(15), nullable=False, primary_key=True)
    port = db.Column(db.Integer)
    username = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(20), nullable=False)
    image_dir = db.Column(db.String(50), db.ForeignKey('sys_set.image_dir'), nullable=False)


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
        'role': user.role,
        'cluster_info': connect.cluster_info
    }
    if context.get('avatar') is None:
        context.pop('avatar')
    return render_template('index.html', **context)


def _get_node_info():
    '''

    :return:[(ip, port, username, password, dir),....]
    '''
    nodes = Node.query.filter().all()
    nodes_info = []
    for node in nodes:
        ip = str(node.ip)
        port = int(node.port)
        username = str(node.username)
        password = str(node.password)
        image_dir = str(node.image_dir)
        nodes_info.append((ip, port, username, password, image_dir))
    return nodes_info


if __name__ == '__main__':
    nodes_info = _get_node_info()
    connect = ConnectNode(nodes_info)
    connect.create_demo()
    db.create_all()
    try:
        app.run(debug=True)
    finally:
        connect.close_demo()
        connect.close()
