#!coding:utf-8
import sys
import datetime
import threading
sys.path.append('../')
from base import *
from tool import Tools, Message, Event
from flask import render_template, redirect, session, url_for, request
import json

THREAD_LOAD_FILE_RUNNING = None


@app.route('/load/file/', methods=['GET', 'POST'])
def load_file():
    if 'username' not in session:
        return render_template('page-login.html')
    elif 'lock_stat' in session:
        return redirect(url_for('lock'))
    return render_template('load-file.html')


@app.route('/load/url/', methods=['GET', 'POST'])
def load_url():
    cluster_info = {
        'master_ip': '10.42.0.74'
    }
    return render_template('load-url.html', cluster_info=cluster_info)


@app.route('/load/info/', methods=['POST'])
def get_load_info():
    """
    Interact with the previous ajax.
    :return: Returns the json string containing the relevant information.
    """
    global THREAD_LOAD_FILE_RUNNING
    received = request.get_json()
    info = {}
    if 'username' in session:
        files_name = received.get('files_name')
        if received.get('type') == 'submit_load':
            ip = received.get('node')
            files_name = received.get('files_name')
            print THREAD_LOAD_FILE_RUNNING
            print check_thread_busy()
            if not check_thread_busy():
                THREAD_LOAD_FILE_RUNNING = threading.Thread(target=load_image_file,
                                                            args=(ip, files_name, session['username']),
                                                            name='thread-load-file')
                THREAD_LOAD_FILE_RUNNING.setDaemon(True)
                THREAD_LOAD_FILE_RUNNING.start()
                info['load_file_status'] = 'success'
            else:
                info['load_file_status'] = 'busy'
    return json.dumps(info)


def load_image_file(ip, files_name, username):
    """
    Load the image file to the docker mirrored repository.
    :param node: Node ip.
    :param files_name: Filename list.
    :param username: The current login user name.
    :return: There is no return value.
    """
    Message.write_message('开始加载镜像文件,清稍候', username)
    connect_node = Tools.get_connect_node()
    connect_node.bool_flush = False
    while connect_node.flush_status:
        pass
    exec_status = []
    cmd = 'docker load < {path}/{filename}'
    path = connect_node.get_ip_attr(ip, 'dir')
    for file_name in files_name:
        load_cmd = cmd.format(path=path, filename=file_name)
        # exec load cmd
        result = connect_node.cmd(ip, load_cmd)
        exec_status.append(result[1])
    success_num = len([x for x in exec_status if x == 'success'])
    fail_num = len(exec_status) - success_num
    message_info = '镜像加载完成:%d成功 %d失败' % (success_num, fail_num)
    if 'defeated' in exec_status:
        Message.write_message(message_info, username, grade='danger')
    else:
        Message.write_message(message_info, username)
        Event.write_event(username, '向{ip}加载了 {number_file} 个镜像文件'.format(ip=ip, number_file=success_num),
                          datetime.datetime.now())
    connect_node.bool_flush = True


def check_thread_busy():
    """
    Check the thread running state.
    :return: Bool. Busy is True, otherwise is False.
    """
    global THREAD_LOAD_FILE_RUNNING
    if THREAD_LOAD_FILE_RUNNING is not None:
        print THREAD_LOAD_FILE_RUNNING.isAlive()
        if not THREAD_LOAD_FILE_RUNNING.isAlive():
            THREAD_LOAD_FILE_RUNNING = None
            busy_status = False
        else:
            busy_status = True
    else:
        busy_status = False
    return busy_status
