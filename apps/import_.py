#!coding:utf-8
import sys
sys.path.append('../')
from common import *
from tool import Tools
from flask import render_template, redirect, session, url_for, request
import json


@app.route('/import/port/')
def import_port():
    if 'username' not in session:
        return render_template('page-login.html')
    elif 'lock_stat' in session:
        return redirect(url_for('lock'))
    return render_template('import-port.html')


@app.route('/import/file/', methods=['GET', 'POST'])
def import_file():
    cluster_info = {
        'master_ip': '10.42.0.74'
    }
    return render_template('import-file.html', cluster_info=cluster_info)


@app.route('/import/info/', methods=['POST'])
def get_import_info():
    """

    :return:{'node_list':[ip1, ip2,,,,], 'image_file_list': [[id, name, create_time, size],...]}
    """
    received = request.get_json()
    info = {'node_list': [], 'image_file_list': []}
    master_node_ip = Sys.query.filter().first().master_node
    if received.get('type') == 'node_list':
        all_node_list = Node.query.filter().all()
        if 'username' in session:
            user_role = User.query.filter(User.username == session.get('username')).first().role
            for node in all_node_list:
                if node.ip != master_node_ip:
                    info.get('node_list').append(node.ip)
                else:
                    if user_role == 'warden':
                        info.get('node_list').append(node.ip)
    elif received.get('type') == 'image_file_list':
        info['image_file_list'] = Tools.get_connect_node().get_image_file_list(master_node_ip)
    else:
        pass
    return json.dumps(info)


def _get_image_file_list(cmd):
    """
    :return
    :param cmd:
    :return:
    """
    pass