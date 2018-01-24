# coding=utf-8
import commands
import sys
import datetime
import threading
import shutil
sys.path.append('../')
from base import *
from config import *
from tool import Tools, Event, Message
from flask import render_template, redirect, session, url_for, request, make_response, send_file
import json


THREAD_PACK_PORT_RUNNING = None
THREAD_PACK_LOCAL_RUNNING = None
DOWNLOAD_PACK_STATUS = False


@app.route('/pack/', methods=['GET', 'POST'])
def pack():
    if 'username' not in session:
        return render_template('page-login.html')
    elif 'lock_stat' in session:
        return redirect(url_for('lock'))
    nodes = Node.query.filter().all()
    if len(nodes) == 0:
        return redirect(url_for('sys_set'))
    if os.path.exists(TEMP_FOLDER):
        shutil.rmtree(TEMP_FOLDER)
    os.mkdir(TEMP_FOLDER)
    return render_template('pack.html')


# 返回下载response
@app.route('/pack/download/')
def pack_download():
    global DOWNLOAD_PACK_STATUS
    if os.path.exists(TEMP_FOLDER + '/Pack.tar') and DOWNLOAD_PACK_STATUS:
        response = make_response(send_file(TEMP_FOLDER + '/Pack.tar'))
        response.headers["Content-Disposition"] = "attachment; filename=Pack.tar;"
        DOWNLOAD_PACK_STATUS = False
        return response


@app.route('/pack/info/', methods=['POST'])
def get_pack_info():
    """处理前台请求
    # 基本思路：
    # 1. 提取ajax请求的json数据
    # 2. 判断请求类别
    # 3. 判断是否有同类线程正在执行,若有,返回线程繁忙,否则,调用多线程执行请求
    # 4. 返回执行结果
    :return: info字典
    """
    global THREAD_RM_IMAGE_RUNNING, THREAD_RM_TAR_RUNNING
    receive = request.get_json()
    receive_type = receive.get('type')
    select_node_ip = receive.get('node')
    images_name = receive.get('files_name')
    info = {}
    if 'username' in session:
        # 响应节点按钮
        if receive_type == 'submit_pack_port':
            if not check_thread_busy('port'):
                THREAD_PACK_PORT_RUNNING = threading.Thread(target=pack_port,
                                                            args=(select_node_ip, images_name, session['username']),
                                                            name='thread-pack-port')
                THREAD_PACK_PORT_RUNNING.setDaemon(True)
                THREAD_PACK_PORT_RUNNING.start()
                info['pack_port_status'] = 'success'
            else:
                info['pack_port_status'] = 'busy'
        # 响应本地按钮
        elif receive_type == 'submit_pack_local':
            if not check_thread_busy('local'):
                THREAD_PACK_LOCAL_RUNNING = threading.Thread(target=pack_local,
                                                             args=(select_node_ip, images_name, session['username']),
                                                             name='thread-pack-local')
                THREAD_PACK_LOCAL_RUNNING.setDaemon(True)
                THREAD_PACK_LOCAL_RUNNING.start()
                info['pack_local_status'] = 'success'
            else:
                info['pock_local_status'] = 'busy'
        # 响应下载状态
        elif receive_type == 'download':
            info['download_status'] = DOWNLOAD_PACK_STATUS
    return json.dumps(info)


def pack_port(ip, images_name, username):
    """
    将docker镜像文件打包成tar文件放入操作节点的镜像文件夹目录下
    :param ip: 操作节点ip
    :param images_name: docker镜像列表
    :param username: 用户名
    :return: 无返回值
    """
    Message.write_message('开始打包镜像文件,清稍候', username)
    connect_node = Tools.get_connect_node()
    connect_node.bool_flush = False
    while connect_node.flush_status:
        pass
    exec_status = []
    # 前台传来的文件名格式为 镜像名:版本号
    cmd = 'docker save {image_name} > {docker_path}/{image_name}.tar'
    docker_path = connect_node.get_ip_attr(ip, 'dir')
    for image_name in images_name:
        # 将镜像名中的'/'转化为'_'
        if '/' in image_name:
            image_name = image_name.replace('/', '_')
        exec_cmd = cmd.format(image_name=image_name, docker_path=docker_path)
        result = connect_node.cmd(ip, exec_cmd)
        exec_status.append(result[1])
    success_num = len([x for x in exec_status if x == 'success'])
    fail_num = len(exec_status) - success_num
    message_info = '镜像打包完成:%d成功 %d失败' % (success_num, fail_num)
    if 'defeated' in exec_status:
        Message.write_message(message_info, username, grade='danger')
    else:
        Message.write_message(message_info, username)
        Event.write_event(username, '从{ip}打包了 {number_file} 个镜像文件'.format(ip=ip, number_file=success_num),
                          datetime.datetime.now())
    connect_node.bool_flush = True


def pack_local(ip, images_name, username):
    """将docker镜像打包为tar文件后返回
    # 基本思路：
    # 1. 将所选Docker镜像导出到执行节点的/tmp/dockerImage目录下
    # 2. 在该节点进行压缩
    # 3. 将压缩完的文件发送到服务所在节点
    # 4. 删除所有临时文件
    # 5. 返回下载请求
    :param ip: 操作节点IP
    :param images_name: docker镜像名列表
    :param username: 操作用户
    :return: 无返回值
    """
    global DOWNLOAD_PACK_STATUS
    Message.write_message('开始打包Docker镜像,请等待', username)
    connect_node = Tools.get_connect_node()
    connect_node.bool_flush = False
    while connect_node.flush_status:
        pass
    node_username = connect_node.get_ip_attr(ip, 'username')
    exec_status = []
    mk_cmd = 'mkdir -p {node_tmp_image_folder}'.format(node_tmp_image_folder=NODE_TMP_IMAGE_FOLDER)
    save_cmd = 'docker save {image_name} > {node_tmp_image_folder}/{image_name}.tar'
    # tar打包不包含路径使用格式 tar -cf `打包文件生成的路径` -C `源文件所在的目录` 源文件所在的路径
    tag_cmd = 'tar -cf {node_tmp_folder}/Pack.tar -C {node_tmp_image_folder} {node_tmp_image_folder}.'
    send_cmd = 'scp -r {username}@{node_ip}:{node_tmp_folder}/Pack.tar {local_path}'
    rm_cmd = 'rm -rf {node_tmp_image_folder} {node_tmp_folder}/Pack.tar'
    # 创建临时文件夹
    connect_node.cmd(ip, mk_cmd)
    # 将所选镜像文件导出
    for image_name in images_name:
        if '/' in image_name:
            image_name = image_name.replace('/', '_')
        exec_save_cmd = save_cmd.format(image_name=image_name, node_tmp_image_folder=NODE_TMP_IMAGE_FOLDER)
        result = connect_node.cmd(ip, exec_save_cmd)
        exec_status.append(result[1])
    # 对打包的镜像文件进行压缩
    exec_tag_cmd = tag_cmd.format(node_tmp_image_folder=NODE_TMP_IMAGE_FOLDER, node_tmp_folder=NODE_TMP_FOLDER)
    connect_node.cmd(ip, exec_tag_cmd)
    # 将文件发送到服务器所在节点
    exec_send_cmd = send_cmd.format(username=node_username, node_ip=ip, node_tmp_folder=NODE_TMP_FOLDER, local_path=TEMP_FOLDER)
    commands.getstatusoutput(exec_send_cmd)
    connect_node.bool_flush = True
    # 删除临时文件
    exec_rm_cmd = rm_cmd.format(node_tmp_image_folder=NODE_TMP_IMAGE_FOLDER, node_tmp_folder=NODE_TMP_FOLDER)
    connect_node.cmd(ip, exec_rm_cmd)
    # 统计执行结果
    success_num = len([x for x in exec_status if x == 'success'])
    fail_num = len(exec_status) - success_num
    message_info = '镜像打包完成:%d成功 %d失败' % (success_num, fail_num)
    if 'defeated' in exec_status:
        Message.write_message(message_info, username, grade='danger')
    else:
        Message.write_message(message_info, username)
        Event.write_event(username, '从{ip}导出了 {number_file} 个镜像文件'.format(ip=ip, number_file=success_num),
                          datetime.datetime.now())
    DOWNLOAD_PACK_STATUS = True


def check_thread_busy(check_type):
    """
    检查是否有任务正在进行
    :param check_type:检查类别.值为 `port` or `local`,其余值会被忽略
    :return:  `True`: 线程繁忙; `False`: 线程结束
    """
    global THREAD_PACK_LOCAL_RUNNING, THREAD_PACK_PORT_RUNNING
    if check_type is 'port':
        if THREAD_PACK_PORT_RUNNING is not None:
            if not THREAD_PACK_PORT_RUNNING.isAlive():
                THREAD_PACK_PORT_RUNNING = None
                busy_status = False
            else:
                busy_status = True
        else:
            busy_status = False
    elif check_type is 'local':
        if THREAD_PACK_LOCAL_RUNNING is not None:
            if not THREAD_PACK_LOCAL_RUNNING.isAlive():
                THREAD_PACK_LOCAL_RUNNING = None
                busy_status = False
            else:
                busy_status = True
        else:
            busy_status = False
    else:
        busy_status = None
    return busy_status