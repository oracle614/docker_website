#!coding:utf-8
import sys
import json
import datetime
sys.path.append('../')
from common import *
from tool import Tools
from flask import render_template, redirect, session, url_for, request
from tool import Event



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
        1. If the type=node_list in the json sent by ajax, the server will return the processed IP list;
        2. If the type=image_file_list in json sent by ajax, the server returns the image file list of the main node,
    which is stored in the key {image_file_list}
        3. If type=submit in the json sent by ajax, the server will return the overall execution result of the import
    request and the execution result at each node, corresponding to the key {import_status} and import_node_status,
    The server will return the image file list at the same time to build a new image file list
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
            if user_role == 'warden':
                info['node_list'] = Tools.get_connect_node().get_ip_list(master=False)
            else:
                info['node_list'] = Tools.get_connect_node().get_ip_list(master=False)
    elif received.get('type') == 'image_file_list':
        info['image_file_list'] = Tools.get_connect_node().get_image_file_list(master_node_ip)
    elif received.get('type') == 'submit':
        node_list = received.get('node_list')
        files_name = received.get('files_name')
        info['image_file_list'] = Tools.get_connect_node().get_image_file_list(master_node_ip)
        # info['import_status'] = Tools
        exec_status = import_master_image_file(node_list, files_name)
        if 'defeated' in exec_status:
            info['import_status'] = 'defeated'
        else:
            info['import_status'] = 'success'
        temp = {}
        for index in xrange(len(node_list)):
            temp[node_list[index]] = exec_status[index]
        info['import_node_status'] = temp
        Event.write_event(session.get('username'), '从master节点导入了 {number_file} 个镜像文件到 {number_node} 个slave节点'.format(
            number_file=len(files_name), number_node=len(node_list)), datetime.datetime.now())
    else:
        pass
    return json.dumps(info)


def import_master_image_file(node_ip_list, files_name):
    """
    Sends the specified file to the specified IP and returns the execution in each node.
    :param node_ip_list: IP Lists, such as [10.42.0.41, ...]
    :param files_name: file name list
    :return: The execution of each node, such as ['success', 'defeated']
    """
    connect_node = Tools.get_connect_node()
    connect_node.bool_flush = False
    while connect_node.flush_status:
        pass
    master_ip = Sys.query.filter().first().master_node
    master_ip_info = connect_node.get_ip_attr(master_ip, 'info')
    master_username = connect_node.get_ip_attr(master_ip, 'username')
    master_path = connect_node.get_ip_attr(master_ip, 'dir')
    exec_status = []
    if master_ip in node_ip_list:
        node_ip_list.remove(master_ip)
    # eg: scp -r pirate@10.42.0.74:/path/test.tar pirate@10.42.0.101:/path
    import_master_cmd = 'scp -r {master_ip_path}/{file} ' \
                        '{node_username}@{node_ip}:{node_ip_path}/'
    for node in node_ip_list:
        node_username = connect_node.get_ip_attr(node, 'username')
        node_ip_path = connect_node.get_ip_attr(node, 'dir')
        for file_name in files_name:
            cmd = import_master_cmd.format(master_ip_path=master_path,file=file_name,
                                           node_username=node_username, node_ip_path=node_ip_path, node_ip=node)
            print cmd
            result = connect_node.cmd(master_ip_info, cmd)
            exec_status.append(result[1])
    connect_node.bool_flush = True
    return exec_status
