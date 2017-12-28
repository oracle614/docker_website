#!coding:utf-8
import sys
import json
sys.path.append('../')
reload(sys)
sys.setdefaultencoding('utf8')
from flask import render_template
from tool import *
from config import EVENT_NUMBER


@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    elif 'lock_stat' in session:
        return redirect(url_for('lock'))
    cluster_info = Tools.get_connect_node().cluster_info
    return render_template('index.html', cluster_info=cluster_info)


@app.route('/event/', methods=['POST'])
def get_index_event():
    """
    Return time dictionary information
    :return: {'events': [{'username': ,avatar': ,'date': ,'event_info':  }, ......]}
    """
    event = {'events': Event.get_event(EVENT_NUMBER)}
    return json.dumps(event)