#!coding:utf-8
import sys
sys.path.append('../')
from common import *
from tool import Tools
from flask import render_template, redirect, session, url_for, request
import json
from tool import *


@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    elif 'lock_stat' in session:
        return redirect(url_for('lock'))
    cluster_info = Tools.get_connect_node().cluster_info
    print cluster_info
    return render_template('index.html', cluster_info=cluster_info)


@app.route('/event/', methods=['POST'])
def get_index_event():
    """
    Return time dictionary information
    :return: {'events': [{'username': ,avatar': ,'date': ,'event_info':  }, ......]}
    """
    print request.get_json()
    event = {'events': Event.get_event(10)}
    print event
    return json.dumps(event)