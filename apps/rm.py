import sys
sys.path.append('../')
from base import *
from tool import Tools
from flask import render_template, redirect, session, url_for, request
import json


@app.route('/rm/file/', methods=['GET', 'POST'])
def rm_file():
    cluster_info = {
        'master_ip': '10.42.0.74'
    }
    return render_template('rm-tar.html', cluster_info=cluster_info)


@app.route('/rm/image/', methods=['GET', 'POST'])
def rm_image():
    cluster_info = {
        'master_ip': '10.42.0.74'
    }
    return render_template('rm-image.html', cluster_info=cluster_info)