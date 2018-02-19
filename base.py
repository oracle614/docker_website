# coding=utf-8
from flask import Flask, session, request
from flask_sqlalchemy import SQLAlchemy
import config
import json


app = Flask(__name__)
app.config.from_object(config)
# 将当前应用上下文推入
app.app_context().push()
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
    # image_dir = db.Column(db.String(50), nullable=False, primary_key=True)
    master_node = db.Column(db.String(20), nullable=False, primary_key=True)


# node set table
class Node(db.Model):
    __tablename__ = 'node_set'
    ip = db.Column(db.String(15), nullable=False, primary_key=True)
    port = db.Column(db.Integer)
    username = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(20), nullable=False)
    image_dir = db.Column(db.String(50), nullable=False)
    available = db.Column(db.String(5))
    # image_dir = db.Column(db.String(50), db.ForeignKey('sys_set.image_dir'), nullable=False)


# event table
class EventInfo(db.Model):
    __tablename__ = 'event'
    event_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    username = db.Column(db.String(10), db.ForeignKey('user.username'), nullable=False)
    event = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    avatar = db.Column(db.String(300))


# message table
class MessageInfo(db.Model):
    __tablename__ = 'message'
    message_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    info = db.Column(db.Text, nullable=False)
    username = db.Column(db.String(10), db.ForeignKey('user.username'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    grade = db.Column(db.String(10), nullable=False)
    # Read status
    status = db.Column(db.String(10), nullable=False)


db.create_all()
