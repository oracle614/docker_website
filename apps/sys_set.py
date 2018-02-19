# coding=utf-8
import sys
import json
import datetime
import werkzeug
import os
import shutil
import threading
import re
reload(sys)
sys.setdefaultencoding('utf8')
sys.path.append('../')
from base import *
from flask import render_template, redirect, session, url_for, request
from config import DEFAULT_IMAGE_FILE_PATH, DEFAULT_NODE_ACCOUNT, DEFAULT_NODE_PORT, DEFAULT_NODE_PASSWORD
from tool import Event
from tool import Message
from tool import Tools


@app.route('/sys/')
def sys_set():
    if 'username' not in session:
        return render_template('page-login.html')
    elif 'lock_stat' in session:
        return redirect(url_for('lock'))
    default_set = {'DEFAULT_IMAGE_FILE_PATH': DEFAULT_IMAGE_FILE_PATH,
                   'DEFAULT_NODE_ACCOUNT': DEFAULT_NODE_ACCOUNT,
                   'DEFAULT_NODE_PASSWORD': DEFAULT_NODE_PASSWORD,
                   'DEFAULT_NODE_PORT': DEFAULT_NODE_PORT}
    return render_template('sys-set.html', default_set=default_set)


@app.route('/user/info/', methods=['POST'])
def get_sys_info():
    result = {}
    received = request.get_json()
    if 'username' in session:
        # 获取节点信息列表
        if received.get('type') == 'sys_info':
            result['sys_info_status'] = 'success'
            result['sys_info_list'] = Tools.get_sys_info_list()
        elif received.get('type') == 'sys_add':
            ip = received.get('ip')
            port = received.get('port')
            account = received.get('account')
            password = received.get('password')
            position = received.get('position')
            # 检查是否输入为空
            if len(account) == 0:
                account = DEFAULT_NODE_ACCOUNT
            if len(password) == 0:
                password = DEFAULT_NODE_PASSWORD
            if len(port) == 0:
                port = DEFAULT_NODE_PORT
            if len(position) == 0:
                position = DEFAULT_IMAGE_FILE_PATH
            # 校验输入
            if check_sys(ip=ip, port=port, account=account, password=password, image_dir=position):
                try:
                    node = Node(ip=ip, port=int(port), username=account, password=password, image_dir=position)
                    # master_ip = Sys.query.filter().first()
                    # 检查是否有主节点,若没有,则指定该节点为主节点
                    # if master_ip is None:
                    #     master_node = Sys(master_node=ip)
                    #     db.session.add(master_node)
                    db.session.add(node)
                    db.session.commit()
                    result['sys_add_status'] = 'success'
                    result['sys_info_list'] = Tools.get_sys_info_list()
                except Exception, e:
                    result['sys_add_status'] = 'danger'
                    result['sys_add_err_reason'] = '数据库写入出错'
            else:
                result['sys_add_status'] = 'danger'
                result['sys_add_err_reason'] = '添加失败,请检查数据格式或当前账户权限'
        elif received.get('type') == 'sys_edit':
            ip = received.get('ip')
            port = received.get('port')
            account = received.get('account')
            password = received.get('password')
            position = received.get('position')
            old_ip = received.get('old_ip')
            # 检查是否输入为空
            if len(account) == 0:
                account = DEFAULT_NODE_ACCOUNT
            elif len(password) == 0:
                password = DEFAULT_NODE_PASSWORD
            elif len(port) == 0:
                port = DEFAULT_NODE_PORT
            elif len(position) == 0:
                position = DEFAULT_IMAGE_FILE_PATH
            # 检查是否改动ip
            if old_ip == ip:
                check_type = 'edit'
            else:
                check_type = 'add'
            if check_sys(ip=ip, port=port, account=account, password=password, image_dir=position, check_type=check_type):
                try:
                    node = Node.query.filter(Node.ip == old_ip).first()
                    node.port = port
                    node.ip = ip
                    node.username = account
                    node.password = password
                    node.image_dir = position
                    db.session.add(node)
                    db.session.commit()
                    result['sys_edit_status'] = 'success'
                    result['sys_info_list'] = Tools.get_sys_info_list()
                except Exception, e:
                    result['sys_edit_status'] = 'danger'
                    result['sys_edit_err_reason'] = '数据库写入出错'
            else:
                result['sys_edit_status'] = 'danger'
                result['sys_edit_err_reason'] = '修改失败,请检查数据格式或当前账户权限'
        elif received.get('type') == 'get_sys_info':
            ip = received.get('ip')
            if ip is not None:
                node = Node.query.filter(Node.ip == ip).first()
                if node is not None:
                    node_info = {'ip': ip, 'port': node.port, 'account': node.username,
                                 'password': node.password, 'position': node.image_dir}
                    result['get_sys_info'] = node_info
                    result['get_sys_status'] = 'success'
                else:
                    result['get_sys_status'] = 'error'
                    result['get_sys_err_reason'] = '账户不存在'
            else:
                result['get_sys_status'] = 'error'
                result['get_sys_err_reason'] = '请求数据不合法'
        elif received.get('type') == 'sys_del':
            ip = received.get('ip')
            if ip is not None:
                # 检测ip是是否存在
                node = Node.query.filter(Node.ip == ip).first()
                if node is not None:
                    # 检查是否是主节点
                    if not Tools.get_connect_node().get_ip_attr(ip, 'master'):
                        now_user = User.query.filter(User.username == session['username']).first()
                        # 检查权限
                        if now_user.role == 'warden':
                            # 删除操作
                            db.session.delete(node)
                            db.session.commit()
                            result['sys_info_list'] = Tools.get_sys_info_list()
                            result['sys_del_status'] = 'success'
                        else:
                            result['sys_del_status'] = 'error'
                            result['sys_del_err_reason'] = '权限不足'
                    else:
                        result['sys_del_status'] = 'error'
                        result['sys_del_err_reason'] = '禁止删除主节点'
            else:
                result['sys_del_status'] = 'error'
                result['sys_del_err_reason'] = '账户不存在'
    return json.dumps(result)


def check_sys(ip, port, account, password, image_dir, check_type='add'):
    """检查请求数据是否合法
    :param check_type:检查类型,值为`edit`或'add'.`add`:当ip存在于数据库中时会返回False;`edit`: 当ip不存在数据库中时返回False
    :param password: 节点密码
    :param ip: 节点ip
    :param port: 节点端口
    :param account: 节点帐号
    :param image_dir: 节点镜像文件存放位置
    :return: 返回boolean类型.True表示检查通过.False表示检查未通过
    """
    # 检测长度是否合法
    if len(ip) > 15 or len(password) > 20 or len(account) > 20 or len(image_dir) > 50:
        return False
    # 检测ip是否已存在
    node = Node.query.filter(Node.ip == ip).first()
    if node is not None:
        # 若检查类型是add,则账户不存在时返回True;若检查类型是edit,则账户不存在时返回false
        if check_type == 'add':
            return False
    # 检查权限
    if 'username' in session:
        user = User.query.filter(User.username == session['username']).first()
        if user.role != 'warden':
            return False
    else:
        return False
    # 检查ip格式是否合法
    pattern_str = r'^(?:(?:1[0-9][0-9]\.)|(?:2[0-4][0-9]\.)|(?:25[0-5]\.)|(?:[1-9][0-9]\.)|(?:[0-9]\.))' \
              r'{3}(?:(?:1[0-9][0-9])|(?:2[0-4][0-9])|(?:25[0-5])|(?:[1-9][0-9])|(?:[0-9]))$'
    pattern = re.compile(pattern_str)
    if pattern.match(ip) is None:
        return None
    return True