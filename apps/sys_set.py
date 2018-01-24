# coding=utf-8
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
from config import DEFAULT_AVATAR_PATH
from tool import Event
from tool import Message
from tool import Tools


@app.route('/sys/')
def sys_set():
    if 'username' not in session:
        return render_template('page-login.html')
    elif 'lock_stat' in session:
        return redirect(url_for('lock'))
    return render_template('sys-set.html')


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
            if len(account) == 0:
                account = DEFAULT_AVATAR_PATH
            try:
                node = Node(ip=ip, port=port, username=account, password=password, image_dir=position)
                master_ip = Sys.query.filter().first()
                # 检查是否有主节点,若没有,则指定该节点为主节点
                if master_ip is None:
                    master_node = Sys(master_node=ip)
                    db.session.add(master_node)
                db.session.add(node)
                db.session.commit()
                result['sys_add_status'] = 'success'
                result['sys_info_list'] = Tools.get_sys_info_list()
            except Exception, e:
                result['sys_add_status'] = 'danger'
        elif received.get('type') == 'sys_edit':
            ip = received.get('ip')
            port = received.get('port')
            account = received.get('account')
            password = received.get('password')
            position = received.get('position')
            if len(account) == 0:
                account = DEFAULT_AVATAR_PATH
            try:
                node = Node.query.filter(Node.ip == ip).first()
                node.port = port
                node.username = account
                node.password = password
                node.image_dir = position
                db.session.add(node)
                db.session.commit()
                result['sys_edit_status'] = 'success'
                result['sys_info_list'] = Tools.get_sys_info_list()
            except Exception, e:
                result['sys_add_status'] = 'danger'
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
    print result
    return json.dumps(result)


def check_sys(username, password, email, avatar, role, info, type='add'):
    """检测账户相关属性是否合法
    :param type: 检查类型.值为`edit`或`add`
    :param username: 用户名
    :param password: 密码
    :param email: 邮箱
    :param avatar: 头像
    :param role: 角色
    :param info: 简介
    :return: Bool值,`True`表示通过检测,`False`表示未通过检测
    """
    # 检测长度是否合法
    if len(username) > 10 or len(password) > 16 or len(password) < 0 or len(username) < 0 \
            or len(role) == 0 \
            or len(email) > 50 \
            or len(avatar) > 300:
        return False
    if role != 'ordinary' and role != 'warden':
        return False
    # 检测账户是否已存在
    user = User.query.filter(User.username == username).first()
    if user is not None:
        # 若检查类型是add,则账户不存在时返回True;若检查类型是edit,则账户不存在时返回false
        if type == 'add':
            return False
    # 检查权限
    if 'username' in session:
        user = User.query.filter(User.username == session['username']).first()
        if user.role != 'warden':
            return False
    else:
        return False
    return True