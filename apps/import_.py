#!coding:utf-8
import sys
import json
import datetime
import werkzeug
import os
import shutil
import threading
reload(sys)
sys.setdefaultencoding('utf8')
sys.path.append('../')
from base import *
from flask import render_template, redirect, session, url_for, request
from tool import Event
from tool import Message
from tool import Tools


ALLOWED_EXTENSIONS = set(['tar'])
thread_import_port_running = None
thread_import_local_running = None


@app.route('/import/port/')
def import_port():
    if 'username' not in session:
        return render_template('page-login.html')
    elif 'lock_stat' in session:
        return redirect(url_for('lock'))
    nodes = Node.query.filter().all()
    if len(nodes) == 0:
        return redirect(url_for('sys_set'))
    return render_template('import-port.html')


@app.route('/import/file/', methods=['GET', 'POST'])
def import_file():
    if 'username' not in session:
        return render_template('page-login.html')
    elif 'lock_stat' in session:
        return redirect(url_for('lock'))
    nodes = Node.query.filter().all()
    if len(nodes) == 0:
        return redirect(url_for('sys_set'))
    if request.method == 'GET':
        # Clear upload file
        upload_folder = app.config['UPLOAD_FOLDER']
        if os.path.exists(upload_folder):
            shutil.rmtree(upload_folder)
        os.makedirs(upload_folder)
        print upload_folder
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
        # 1. If the type=node_list in the json sent by ajax, the server will return the processed IP list;
        2. If the type=image_file_list in json sent by ajax, the server returns the image file list of the main node,
    which is stored in the key {image_file_list};
        3. If type=submit_port in the json sent by ajax, the server will return the overall execution result of the import
    request and the execution result at each node, corresponding to the key {import_status} and import_node_status,
    The server will return the image file list at the same time to build a new image file list;
        4. If type=add_upload_file, the server verifies that the file_name sent by ajax is present in the upload file.
    Returns success when it exists, otherwise it returns a defeated.
        5. If type=remove_upload_file, the server deletes the folder in the request json from the upload folder of the
    project root directory, and if successful, the server returns success or returns the defeated.
        6. If type=submit_local, the server will send all the files in the server root directory upload directory to
    the node node specified in the ajax request.

    :return:
        # 1. Ip list. Like as [Ip1, Ip2, ...],in the 'node_list' item in the 'info' dictionary
        2. Image file list. in the 'image_file_list' item in the 'info' dictionary. Format to 'see get_image_file_list()'
        3. Main node import result.The overall execution is stored in the import_port_status key of the info dictionary,
    The execution of each node is stored in the import_port_node_status key of the info dictionary, in a dictionary.
        4. File upload status.Returns success when the checksum is successful, otherwise it returns the defeated.
        5. File delete operation status. Successful execution of return success, responsible for returning the defeated.
        6. local import result.The overall execution is stored in the import_local_status key of the info dictionary,
    The execution of each node is stored in the import_local_node_status key of the info dictionary, in a dictionary.
    """
    global thread_import_local_running, thread_import_port_running
    received = request.get_json()
    info = {'node_list': [], 'image_file_list': []}
    master_node_ip = Sys.query.filter().first().master_node
    # Get image file list
    if received.get('type') == 'image_file_list':
        info['image_file_list'] = Tools.get_image_file_list(master_node_ip)
    # Import image file from master node
    elif received.get('type') == 'submit_port':
        node_list = received.get('node_list')
        files_name = received.get('files_name')
        info['image_file_list'] = Tools.get_image_file_list(master_node_ip)
        if not check_thread_busy('port'):
            thread_import_port_running = threading.Thread(target=import_image_file,
                                                          args=('port', node_list, files_name, session['username']),
                                                          name='thread-import-port')
            thread_import_port_running.setDaemon(True)
            thread_import_port_running.start()
            info['import_port_status'] = 'success'
        else:
            info['import_port_status'] = 'busy'
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
        if not check_thread_busy('local'):
            thread_import_local_running = threading.Thread(target=import_image_file,
                                                           args=('local', node_list, files_name, session['username']),
                                                           name='thread-import-local')
            thread_import_local_running.setDaemon(True)
            thread_import_local_running.start()
            info['import_local_status'] = 'success'
        else:
            info['import_local_status'] = 'busy'
    else:
        pass
    return json.dumps(info)


def import_image_file(import_type, node_ip_list, files_name, username):
    """
    Sends the specified file to the specified IP and returns the execution in each node.
    :param node_ip_list: The node IP list to be sent, such as [10.42.0.41, ...]
    :param import_type: The request type.Value as 'port' or 'local'
    :param files_name: File name list
    :return: The execution of each node, such as ['success', 'defeated']
    """
    if import_type == 'port':
        Message.write_message('主节点镜像开始导入', username)
    else:
        Message.write_message('本地镜像开始导入', username)
    connect_node = Tools.get_connect_node()
    connect_node.bool_flush = False
    while connect_node.flush_status:
        pass
    master_ip = Sys.query.filter().first().master_node
    if import_type == 'port':
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
            # 转移'/'
            if '/' in file_name:
                file_name = file_name.replace('/', '_')
            cmd = import_master_cmd.format(sou_path=sou_path, file=file_name,
                                           node_username=node_username, node_ip_path=node_ip_path, node_ip=node)
            print cmd
            result = connect_node.cmd(master_ip, cmd)
            exec_status.append(result[1])
    connect_node.bool_flush = True
    if 'defeated' in exec_status:
        grade = 'danger'
    else:
        grade = 'success'
    if import_type == 'port':
        if grade == 'success':
            Message.write_message('主节点镜像导入成功', username)
            Event.write_event(username, '从主节点导入了 {number_file} 个镜像文件到 {number_node} 个节点'.format(
                number_file=len(files_name), number_node=len(node_ip_list)), datetime.datetime.now())
        else:
            Message.write_message('主节点镜像导入失败', username, grade=grade)
    else:
        if grade == 'success':
            Message.write_message('本地镜像导入成功', username)
            Event.write_event(username, '从本地导入了 {number_file} 个镜像文件到 {number_node} 个节点'.format(
                number_file=len(files_name), number_node=len(node_ip_list)), datetime.datetime.now())
        else:
            Message.write_message('本次镜像导入失败', username, grade=grade)


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


def check_thread_busy(check_type):
    """
    Check thread status
    :param check_type: 'port' or 'local'
    :return: Busy status: True or False
    """
    global thread_import_port_running, thread_import_local_running
    if check_type == 'port':
        if thread_import_port_running is not None:
            if not thread_import_port_running.isAlive():
                thread_import_port_running = None
                busy_status = False
            else:
                busy_status = True
        else:
            busy_status = False
    else:
        if thread_import_local_running is not None:
            if not thread_import_local_running.isAlive():
                thread_import_local_running = None
                busy_status = False
            else:
                busy_status = True
        else:
            busy_status = False
    return busy_status