import sys
sys.path.append('../')
from base import *
from tool import Tools
from flask import render_template, redirect, session, url_for, request
import json


@app.route('/show/file/', methods=['GET', 'POST'])
def show_file():
    if 'username' not in session:
        return render_template('page-login.html')
    elif 'lock_stat' in session:
        return redirect(url_for('lock'))
    nodes = Node.query.filter().all()
    if len(nodes) == 0:
        return redirect(url_for('sys_set'))
    return render_template('show-tar.html')


@app.route('/show/image/', methods=['GET', 'POST'])
def show_image():
    if 'username' not in session:
        return render_template('page-login.html')
    elif 'lock_stat' in session:
        return redirect(url_for('lock'))
    nodes = Node.query.filter().all()
    if len(nodes) == 0:
        return redirect(url_for('sys_set'))
    return render_template('show-image.html')