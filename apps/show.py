import sys
sys.path.append('../')
from base import *
from tool import Tools
from flask import render_template, redirect, session, url_for, request
import json


@app.route('/show/file/', methods=['GET', 'POST'])
def show_file():
    cluster_info = {
        'master_ip': '10.42.0.74'
    }
    return render_template('show-tar.html', cluster_info=cluster_info)


@app.route('/show/image/', methods=['GET', 'POST'])
def show_image():
    cluster_info = {
        'master_ip': '10.42.0.74'
    }
    return render_template('show-image.html', cluster_info=cluster_info)