from flask import Flask, session, request
from flask_sqlalchemy import SQLAlchemy
import config
import json


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
    master_node = db.Column(db.String(20), nullable=False)


# node set table
class Node(db.Model):
    __tablename__ = 'node_set'
    ip = db.Column(db.String(15), nullable=False, primary_key=True)
    port = db.Column(db.Integer)
    username = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(20), nullable=False)
    image_dir = db.Column(db.String(50), db.ForeignKey('sys_set.image_dir'), nullable=False)


# event table
class EventInfo(db.Model):
    __tablename__ = 'event'
    event_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    username = db.Column(db.String(10), db.ForeignKey('user.username'), nullable=False)
    event = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    avatar = db.Column(db.String(300))


@app.route('/head/user/', methods=['POST'])
def get_head_user_info():
    """
    Gets the title bar user information
    :return:{'username': ,'avatar': }
    """
    user_info = None
    if 'username' not in session:
        return user_info
    temp = User.query.filter(User.username == session['username']).first()
    user_info = {'username': temp.username, 'avatar': temp.avatar, 'role': temp.role}
    return json.dumps(user_info)


db.create_all()