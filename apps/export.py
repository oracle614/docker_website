import sys
sys.path.append('../')
from common import *
from tool import Tools
from flask import render_template, redirect, session, url_for, request
import json


@app.route('/export/local/', methods=['GET', 'POST'])
def export_image():
    cluster_info = {
        'master_ip': '10.42.0.74'
    }
    return render_template('export-local.html', cluster_info=cluster_info)