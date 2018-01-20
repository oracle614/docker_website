import sys
import json
import datetime
import werkzeug
import os
import shutil
import threading
reload(sys)
sys.setdefaultencoding('utf8')
sys.path.append('../')
from base import *
from flask import render_template, redirect, session, url_for, request
from tool import Event
from tool import Message
from tool import Tools


@app.route('/user/')
def user_set():
    return render_template('user-set.html')