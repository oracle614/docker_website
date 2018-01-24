# coding=utf-8
import sys

import datetime
import threading

sys.path.append('../')
from base import *
from tool import Tools, Message, Event
from flask import render_template, redirect, session, url_for, request
import json


THREAD_RM_TAR_RUNNING = None
THREAD_RM_IMAGE_RUNNING = None


@app.route('/rm/file/', methods=['GET', 'POST'])
def rm_file():
    if 'username' not in session:
        return render_template('page-login.html')
    elif 'lock_stat' in session:
        return redirect(url_for('lock'))
    nodes = Node.query.filter().all()
    if len(nodes) == 0:
        return redirect(url_for('sys_set'))
    return render_template('rm-tar.html')


@app.route('/rm/info/', methods=['POST'])
def get_rm_info():
    global THREAD_RM_IMAGE_RUNNING, THREAD_RM_TAR_RUNNING
    if 'username' in session:
        receive = request.get_json()
        receive_type = receive.get('type')
        receive_node_ip = receive.get('node')
        receive_files_name = receive.get('files_name')
        info = {}
        if receive_type == 'submit_rm_tar':
            if not check_thread_busy('tar'):
                THREAD_RM_TAR_RUNNING = threading.Thread(target=rm_tar_file,
                                                         args=(receive_node_ip, receive_files_name, session['username']),
                                                         name='thread-rm-tar')
                THREAD_RM_TAR_RUNNING.setDaemon(True)
                THREAD_RM_TAR_RUNNING.start()
                info['rm_tar_status'] = 'success'
            else:
                info['rm_tar_status'] = 'busy'
        elif receive_type == 'submit_rm_image':
            if not check_thread_busy('image'):
                receive_files_status = receive.get('files_status')
                THREAD_RM_IMAGE_RUNNING = threading.Thread(target=rm_image_file,
                                                           args=(receive_node_ip, receive_files_name, receive_files_status, session['username']),
                                                           name='thread-rm-image')
                THREAD_RM_IMAGE_RUNNING.setDaemon(True)
                THREAD_RM_IMAGE_RUNNING.start()
                info['rm_image_status'] = 'success'
            else:
                info['rm_image_status'] = 'busy'
    return json.dumps(info)


@app.route('/rm/image/', methods=['GET', 'POST'])
def rm_image():
    if 'username' not in session:
        return render_template('page-login.html')
    elif 'lock_stat' in session:
        return redirect(url_for('lock'))
    nodes = Node.query.filter().all()
    if len(nodes) == 0:
        return redirect(url_for('sys_set'))
    return render_template('rm-image.html')


def rm_tar_file(ip, files_name, username):
    """
    删除镜像文件
    :param ip:
    :param files_name:
    :param username:
    :return:
    """
    Message.write_message('开始删除镜像文件,清稍候', username)
    connect_node = Tools.get_connect_node()
    connect_node.bool_flush = False
    while connect_node.flush_status:
        pass
    exec_status = []
    cmd = 'rm -rf {path}/{file_name}'
    path = connect_node.get_ip_attr(ip, 'dir')
    # 删除
    for file_name in files_name:
        # 若镜像名中存在'/',则进行转义
        if '/' in file_name:
            file_name = file_name.replace('/', '\/')
        rm_cmd = cmd.format(path=path, file_name=file_name)
        # exec rm cmd
        result = connect_node.cmd(ip, rm_cmd)
        exec_status.append(result[1])
    # 统计执行结果
    success_num = len([x for x in exec_status if x == 'success'])
    fail_num = len(exec_status) - success_num
    message_info = '镜像删除完成:%d成功 %d失败' % (success_num, fail_num)
    if 'defeated' in exec_status:
        Message.write_message(message_info, username, grade='danger')
    else:
        Message.write_message(message_info, username)
        Event.write_event(username, '从{ip}删除了 {number_file} 个镜像文件'.format(ip=ip, number_file=success_num),
                          datetime.datetime.now())
    connect_node.bool_flush = True


def rm_image_file(ip, files_name, files_status, username):
    """删除Docker镜像
    基本思路：
    1. 判断该镜像是否正在被使用
    2. 若该镜像正在被占用,先找出占用该镜像的容器并删除该容器
    3. 删除该镜像
    :param ip:
    :param files_name:
    :param files_status:
    :param username:
    :return:
    """
    # Message.write_message('开始删除Docker镜像,清稍候', username)
    connect_node = Tools.get_connect_node()
    connect_node.bool_flush = False
    while connect_node.flush_status:
        pass
    exec_status = []
    # 获取容器id
    get_container_id = "docker ps -a|awk '/{image_name}/ {{print $1}}'"
    # 停止并删除容器命令
    rm_container_cmd = 'docker kill {container_id} & docker rm {container_id}'
    # 删除镜像
    rm_image_cmd = 'docker rmi {docker_image}'
    # 删除
    for index in xrange(len(files_name)):
        # 若镜像中存在'/',则进行转义
        if '/' in files_name[index]:
            files_name[index] = files_name[index].replace('/', '\/')
        image_name = files_name[index].split(':')[0]
        image_tag = files_name[index].split(':')[1]
        exec_rm_image_cmd = rm_image_cmd.format(docker_image=files_name[index])
        # 如果镜像名为空,则拒绝操作,防止筛选出全部容器
        if len(image_name) == 0:
            return
        # 若镜像未被使用
        if files_status[index] == 'NoUse':
            result = connect_node.cmd(ip, exec_rm_image_cmd)
            exec_status.append(result[1])
        else:
            exec_tag_container_id = get_container_id.format(image_name=files_name[index])
            exec_no_tag_container_id = get_container_id.format(image_name=image_name)
            # 获取id时,首先通过镜像全名获取,若结果为空且本镜像的tag为latest,则以镜像名重新获取一遍
            container_id = connect_node.cmd(ip, exec_tag_container_id)
            container_id_list = container_id[2][0].readlines()
            if len(container_id_list) == 0:
                if image_tag == 'latest':
                    container_id = connect_node.cmd(ip, exec_no_tag_container_id)
                    container_id_list = container_id[2][0].readlines()
            print container_id_list
            # 删除容器
            for container in container_id_list:
                container_id = container.split('\n')[0]
                exec_rm_container_cmd = rm_container_cmd.format(container_id=container_id)
                connect_node.cmd(ip, exec_rm_container_cmd)
            # 删除镜像
            result = connect_node.cmd(ip, exec_rm_image_cmd)
            exec_status.append(result[1])
    # 统计执行结果
    success_num = len([x for x in exec_status if x == 'success'])
    fail_num = len(exec_status) - success_num
    message_info = '镜像删除完成:%d成功 %d失败' % (success_num, fail_num)
    if 'defeated' in exec_status:
        Message.write_message(message_info, username, grade='danger')
    else:
        Message.write_message(message_info, username)
        Event.write_event(username, '从{ip}删除了 {number_file} 个Docker镜像'.format(ip=ip, number_file=success_num),
                          datetime.datetime.now())
    connect_node.bool_flush = True


def check_thread_busy(check_type):
    """
    检查是否有任务正在进行
    :param check_type:检查类别.值为 `tar` or `image`,其余值会被忽略
    :return:  `True`: 线程繁忙; `False`: 线程结束
    """
    global THREAD_RM_TAR_RUNNING, THREAD_RM_IMAGE_RUNNING
    if check_type is 'tar':
        if THREAD_RM_TAR_RUNNING is not None:
            if not THREAD_RM_TAR_RUNNING.isAlive():
                THREAD_RM_TAR_RUNNING = None
                busy_status = False
            else:
                busy_status = True
        else:
            busy_status = False
    elif check_type is 'image':
        if THREAD_RM_IMAGE_RUNNING is not None:
            if not THREAD_RM_IMAGE_RUNNING.isAlive():
                THREAD_RM_IMAGE_RUNNING = None
                busy_status = False
            else:
                busy_status = True
        else:
            busy_status = False
    else:
        busy_status = None
    return busy_status