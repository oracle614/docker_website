#!coding:utf-8
import sys
sys.path.append('../')
from common import *
from tool import Tools
from flask import render_template, redirect, session, url_for, request
import json


@app.route('/load/file/', methods=['GET', 'POST'])
def load_file():
    cluster_info = {
        'master_ip': '10.42.0.74'
    }
    return render_template('load-file.html', cluster_info=cluster_info)


@app.route('/load/url/', methods=['GET', 'POST'])
def load_url():
    cluster_info = {
        'master_ip': '10.42.0.74'
    }
    return render_template('load-url.html', cluster_info=cluster_info)