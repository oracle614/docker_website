#!coding:utf-8
import sys
import json
import datetime
import werkzeug
import os
import shutil
sys.path.append('../')
from common import *
from tool import Tools
from flask import render_template, redirect, session, url_for, request
from tool import Event


ALLOWED_EXTENSIONS = set(['tar'])


@app.route('/import/port/')
def import_port():
    if 'username' not in session:
        return render_template('page-login.html')
    elif 'lock_stat' in session:
        return redirect(url_for('lock'))
    return render_template('import-port.html')


@app.route('/import/file/', methods=['GET', 'POST'])
def import_file():
    if 'username' not in session:
        return render_template('page-login.html')
    elif 'lock_stat' in session:
        return redirect(url_for('lock'))
    if request.method == 'GET':
        # Clear upload file
        upload_folder = app.config['UPLOAD_FOLDER']
        if os.path.exists(upload_folder):
            shutil.rmtree(upload_folder)
            os.makedirs(upload_folder)
        return render_template('import-file.html')
    else:
        file_obj = request.files
        files = file_obj['file']
        # Whether the test file exists and whether the tar suffix is specified (the foreground has been detected).
        if files and allowed_file(files.filename):
            # Check whether the user input file name is valid.
            filename = werkzeug.secure_filename(files.filename)
            files.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return 'success'


def allowed_file(filename):
    """
    Determine whether the suffix of filename is defined in ALLOWED_EXTENSIONS
    :param filename: Filename
    :return: Bool value
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route('/import/info/', methods=['POST'])
def get_import_info():
    """
        1. If the type=node_list in the json sent by ajax, the server will return the processed IP list;
        2. If the type=image_file_list in json sent by ajax, the server returns the image file list of the main node,
    which is stored in the key {image_file_list};
        3. If type=submit in the json sent by ajax, the server will return the overall execution result of the import
    request and the execution result at each node, corresponding to the key {import_status} and import_node_status,
    The server will return the image file list at the same time to build a new image file list;
        4.
    :return:{'node_list':[ip1, ip2,,,,], 'image_file_list': [[id, name, create_time, size],...]}
    """
    received = request.get_json()
    info = {'node_list': [], 'image_file_list': []}
    master_node_ip = Sys.query.filter().first().master_node
    if received.get('type') == 'node_list':
        # Get all node
        if 'username' in session:
            user_role = User.query.filter(User.username == session.get('username')).first().role
            # Only when the current user's role is warden, the IP address of the master node will be displayed in the
            # previous section.
            if user_role == 'warden' and received.get('master'):
                info['node_list'] = Tools.get_connect_node().get_ip_list(master=True)
            else:
                info['node_list'] = Tools.get_connect_node().get_ip_list(master=False)
    # Get image file list
    elif received.get('type') == 'image_file_list':
        info['image_file_list'] = Tools.get_connect_node().get_image_file_list(master_node_ip)
    # Import image file from master node
    elif received.get('type') == 'submit_port':
        node_list = received.get('node_list')
        files_name = received.get('files_name')
        info['image_file_list'] = Tools.get_connect_node().get_image_file_list(master_node_ip)
        exec_status = import_image_file('port', node_list, files_name)
        if 'defeated' in exec_status:
            info['import_port_status'] = 'defeated'
        else:
            info['import_port_status'] = 'success'
        temp = {}
        for index in xrange(len(node_list)):
            temp[node_list[index]] = exec_status[index]
        info['import_port_node_status'] = temp
        Event.write_event(session.get('username'), '从主节点导入了 {number_file} 个镜像文件到 {number_node} 个节点'.format(
            number_file=len(files_name), number_node=len(node_list)), datetime.datetime.now())
    # Get add status
    elif received.get('type') == 'add_upload_file':
        file_name = received.get('file_name')
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
        if os.path.exists(file_path):
            info['add_upload_file_status'] = 'success'
        else:
            info['add_upload_file_status'] = 'defeated'
    # Remove upload file
    elif received.get('type') == 'remove_upload_file':
        file_name = received.get('file_name')
        exec_status = remove_upload_file(file_name)
        info['remove_upload_file_status'] = exec_status
    elif received.get('type') == 'get_upload_file_num':
        info['upload_file_num'] = len(os.listdir(app.config['UPLOAD_FOLDER']))
    # Import image file from local
    elif received.get('type') == 'submit_local':
        node_list = received.get('node_list')
        files_name = os.listdir(app.config['UPLOAD_FOLDER'])
        exec_status = import_image_file('local', node_list, files_name)
        if 'defeated' in exec_status:
            info['import_local_status'] = 'defeated'
        else:
            info['import_local_status'] = 'success'
        temp = {}
        for index in xrange(len(node_list)):
            temp[node_list[index]] = exec_status[index]
        info['import_node_status'] = temp
        Event.write_event(session.get('username'), '从本地导入了 {number_file} 个镜像文件到 {number_node} 个节点'.format(
            number_file=len(files_name), number_node=len(node_list)), datetime.datetime.now())
    else:
        pass
    return json.dumps(info)


def import_image_file(type, node_ip_list, files_name):
    """
    Sends the specified file to the specified IP and returns the execution in each node.
    :param node_ip_list: The node IP list to be sent, such as [10.42.0.41, ...]
    :param type: The request type.Value as 'port' or 'local'
    :param files_name: File name list
    :return: The execution of each node, such as ['success', 'defeated']
    """
    connect_node = Tools.get_connect_node()
    connect_node.bool_flush = False
    while connect_node.flush_status:
        pass
    master_ip = Sys.query.filter().first().master_node
    master_ip_info = connect_node.get_ip_attr(master_ip, 'info')
    if type == 'port':
        sou_path = connect_node.get_ip_attr(master_ip, 'dir')
    else:
        sou_path = app.config['UPLOAD_FOLDER']
    exec_status = []
    # eg: scp -r /path/test.tar pirate@10.42.0.101:/path
    import_master_cmd = 'scp -r {sou_path}/{file} ' \
                        '{node_username}@{node_ip}:{node_ip_path}/'
    for node in node_ip_list:
        node_username = connect_node.get_ip_attr(node, 'username')
        node_ip_path = connect_node.get_ip_attr(node, 'dir')
        for file_name in files_name:
            cmd = import_master_cmd.format(sou_path=sou_path, file=file_name,
                                           node_username=node_username, node_ip_path=node_ip_path, node_ip=node)
            result = connect_node.cmd(master_ip_info, cmd)
            exec_status.append(result[1])
            print cmd
    connect_node.bool_flush = True
    return exec_status


def remove_upload_file(file_name):
    """
        Deletes the specified file from the specified directory.Delete successfully returns 'success',
    otherwise return to 'defeated'
    :param file_name: File name
    :return: Exec status
    """
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
    if os.path.exists(file_path):
        os.remove(file_path)
        return 'success'
    return 'defeated'
