#!coding:utf-8
import sys
import tarfile
import shutil
import time
import json
import datetime
import threading
import commands
sys.path.append('../')
from base import *
from tool import Tools
from flask import render_template, redirect, session, url_for, request, send_file, make_response
from config import *
from tool import Message
from tool import Event


thread_export_local_running = None
tar_export_status = False


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
    global thread_export_local_running
    received = request.get_json()
    info = {}
    if 'username' in session:
        master_node_ip = Sys.query.filter().first().master_node
    # if received.get('type') == 'node_list':
    #     if 'username' in session:
    #         user_role = User.query.filter(User.username == session.get('username')).first().role
    #         # Only when the current user's role is warden, the IP address of the master node will be displayed in the
    #         # previous section.
    #         if user_role == 'warden' and received.get('master'):
    #             info['node_list'] = Tools.get_connect_node().get_ip_list(master=True)
    #         else:
    #             info['node_list'] = Tools.get_connect_node().get_ip_list(master=False)
    # elif received.get('type') == 'image_file_list':
    #     if received.get('recent_time'):
    #         node = received.get('node')
    #         info['image_file_list'] = Tools.get_connect_node().get_image_file_list(node, recent_time=True)
        if received.get('type') == 'submit_export':
            node = received.get('node')
            files_name = received.get('files_name')
            print "submit", thread_export_local_running
            if not check_thread_busy():
                thread_export_local_running = threading.Thread(target=send_files_download,
                                                               args=(node, files_name, session['username']),
                                                               name='thread-export-local')
                thread_export_local_running.setDaemon(True)
                thread_export_local_running.start()
                info['export_local_status'] = 'success'
            else:
                info['export_local_status'] = 'busy'
        elif received.get('type') == 'download':
            info['download_status'] = tar_export_status
        print info
    return json.dumps(info)


@app.route('/export/download/')
def export_download():
    global tar_export_status
    if os.path.exists(os.getcwd() + '/' + 'Download.tar') and tar_export_status:
        response = make_response(send_file('Download.tar'))
        response.headers["Content-Disposition"] = "attachment; filename=Download.tar;"
        tar_export_status = False
        return response


def send_files_download(node, files_name, username):
    global tar_export_status
    Message.write_message('开始打包镜像文件,请等待', username)
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
        # exist error
        # result = connect_node.cmd(master_ip_info, cmd)
        # exec_status.append(result[1])
        status, _ = commands.getstatusoutput(cmd)
        if status == 0:
            status = 'success'
        else:
            status = 'defeated'
        exec_status.append(status)
    print os.listdir(DOWNLOAD_FOLDER)
    with tarfile.open('Download.tar', 'w') as tar:
        for root, dir_, files in os.walk(DOWNLOAD_FOLDER):
            for file_ in files:
                print file_
                full = os.path.join(root, file_)
                tar.add(full, arcname=file_)
    connect_node.bool_flush = True
    success_num = len([x for x in exec_status if x == 'success'])
    fail_num = len(exec_status) - success_num
    message_info = '镜像打包完成:%d成功 %d失败' % (success_num, fail_num)
    if 'defeated' in exec_status:
        Message.write_message(message_info, username, grade='danger')
    else:
        Message.write_message(message_info, username)
        Event.write_event(username, '从{node}导出了 {number_file} 个镜像文件'.format(node=node, number_file=success_num),
                          datetime.datetime.now())
    tar_export_status = True


def check_thread_busy():
    """

    :return:
    """
    global thread_export_local_running
    print thread_export_local_running
    if thread_export_local_running is not None:
        print thread_export_local_running.isAlive()
        if not thread_export_local_running.isAlive():
            thread_export_local_running = None
            busy_status = False
        else:
            busy_status = True
    else:
        busy_status = False
    return busy_status