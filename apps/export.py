import sys
import tarfile
import shutil
import time
sys.path.append('../')
from common import *
from tool import Tools
from flask import render_template, redirect, session, url_for, request, send_file, make_response
import json
from config import *


@app.route('/export/local/', methods=['GET', 'POST'])
def export_image():
    if 'username' not in session:
        return render_template('page-login.html')
    elif 'lock_stat' in session:
        return redirect(url_for('lock'))
    if os.path.exists(DOWNLOAD_FOLDER):
        shutil.rmtree(DOWNLOAD_FOLDER)
        os.makedirs(DOWNLOAD_FOLDER)
    if os.path.exists(HOME_FOLDER + '/Download.tar'):
        os.remove(HOME_FOLDER + '/Download.tar')
    return render_template('export-local.html')


@app.route('/export/info/', methods=['POST'])
def get_export_info():
    received = request.get_json()
    info = {}
    master_node_ip = Sys.query.filter().first().master_node
    if received.get('type') == 'node_list':
        if 'username' in session:
            user_role = User.query.filter(User.username == session.get('username')).first().role
            # Only when the current user's role is warden, the IP address of the master node will be displayed in the
            # previous section.
            if user_role == 'warden' and received.get('master'):
                info['node_list'] = Tools.get_connect_node().get_ip_list(master=True)
            else:
                info['node_list'] = Tools.get_connect_node().get_ip_list(master=False)
    elif received.get('type') == 'image_file_list':
        if received.get('recent_time'):
            node = received.get('node')
            info['image_file_list'] = Tools.get_connect_node().get_image_file_list(node, recent_time=True)
    elif received.get('type') == 'submit_export':
        node = received.get('node')
        files_name = received.get('files_name')
        print files_name
        exec_status = send_files_download(node, files_name)
        if 'defeated' in exec_status:
            info['export_local_status'] = 'defeated'
        else:
            info['export_local_status'] = 'success'
    return json.dumps(info)


@app.route('/export/download/')
def export_download():
    if os.path.exists(os.getcwd() + '/' + 'Download.tar'):
        response = make_response(send_file('Download.tar'))
        response.headers["Content-Disposition"] = "attachment; filename=Download.tar;"
        return response


def send_files_download(node, files_name):
    connect_node = Tools.get_connect_node()
    connect_node.bool_flush = False
    while connect_node.flush_status:
        pass
    master_ip = Sys.query.filter().first().master_node
    master_ip_info = connect_node.get_ip_attr(master_ip, 'info')
    node_username = connect_node.get_ip_attr(node, 'username')
    sou_path = connect_node.get_ip_attr(node, 'dir')
    exec_status = []
    send_cmd = 'scp -r {username}@{node_ip}:{sou_path}/{file} {local_path}'
    for file_name in files_name:
        cmd = send_cmd.format(username=node_username, node_ip=node, sou_path=sou_path, file=file_name, local_path=DOWNLOAD_FOLDER)
        result = connect_node.cmd(master_ip_info, cmd)
        exec_status.append(result[1])
    with tarfile.open('Download.tar', 'w') as tar:
        for root, dir_, files in os.walk(DOWNLOAD_FOLDER):
            for file_ in files:
                print file_
                full = os.path.join(root, file_)
                tar.add(full, arcname=file_)
    connect_node.bool_flush = True
    return exec_status