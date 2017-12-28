import sys
sys.path.append('../')
from base import *
from tool import Tools
from flask import render_template, redirect, session, url_for, request
import json


@app.route('/pack/', methods=['GET', 'POST'])
def pack():
    cluster_info = {
        'master_ip': '10.42.0.74'
    }
    return render_template('pack.html', cluster_info=cluster_info)