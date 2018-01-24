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


@app.route('/user/')
def user_set():
    if 'username' not in session:
        return render_template('page-login.html')
    elif 'lock_stat' in session:
        return redirect(url_for('lock'))
    nodes = Node.query.filter().all()
    if len(nodes) == 0:
        return redirect(url_for('sys_set'))
    return render_template('user-set.html')


@app.route('/user/add/', methods=['POST'])
def get_user_info():
    result = {}
    received = request.get_json()
    if 'username' in session:
        # 添加用户请求
        if received.get('type') == 'user_add':
            username = received.get('username')
            password = received.get('password')
            avatar = received.get('avatar')
            role = received.get('role')
            info = received.get('info')
            email = received.get('email')
            now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if check_user(username=username, password=password, email=email,
                          avatar=avatar, role=role, info=info, type='add'):
                if len(avatar) == 0:
                    avatar = DEFAULT_AVATAR_PATH
                try:
                    user = User(username=username, password=password, email=email, avatar=avatar,
                                role=role, info=info,
                                createtime=now_time)
                    db.session.add(user)
                    db.session.commit()
                    result['user_add_status'] = 'success'
                    result['user_info_list'] = Tools.get_user_info_list()
                except Exception, e:
                    result['user_add_status'] = 'danger'
            else:
                result['user_add_status'] = 'danger'
        elif received.get('type') == 'user_info':
            # 顺序 id-用户名-密码-邮箱-创建日期-角色-简介
            users_list = Tools.get_user_info_list()
            result['user_info_status'] = 'success'
            result['user_info_list'] = users_list
        elif received.get('type') == 'user_del':
            username = received.get('username')
            # 检查是否为自身账户
            if username != session['username']:
                if username is not None:
                    # 检测账户是是否存在
                    user = User.query.filter(User.username == username).first()
                    if user is not None:
                        now_user = User.query.filter(User.username == session['username']).first()
                        if now_user.role == 'warden':
                            # 删除操作
                            db.session.delete(user)
                            db.session.commit()
                            result['user_info_list'] = Tools.get_user_info_list()
                            result['user_del_status'] = 'success'
                        else:
                            result['user_del_status'] = 'error'
                            result['user_del_err_reason'] = '权限不足'
                else:
                    result['user_del_status'] = 'error'
                    result['user_del_err_reason'] = '账户不存在'
            else:
                result['user_del_status'] = 'error'
                result['user_del_err_reason'] = '禁止删除当前账户'
        elif received.get('type') == 'get_user_info':
            username = received.get('username')
            if username is not None:
                user = User.query.filter(User.username == username).first()
                if user is not None:
                    user_info = {'username': user.username, 'password': user.password, 'email': user.email,
                                 'role': user.role, 'info': user.info, 'avatar': user.avatar}
                    result['get_user_info'] = user_info
                    result['get_user_status'] = 'success'
                else:
                    result['get_user_status'] = 'error'
                    result['get_user_err_reason'] = '账户不存在'
            else:
                result['get_user_status'] = 'error'
                result['get_user_err_reason'] = '请求数据不合法'
        elif received.get('type') == 'user_edit':
            username = received.get('username')
            password = received.get('password')
            avatar = received.get('avatar')
            role = received.get('role')
            info = received.get('info')
            email = received.get('email')
            if check_user(username=username, password=password, email=email, avatar=avatar,
                          role=role, info=info, type='edit'):
                if len(avatar) == 0:
                    avatar = DEFAULT_AVATAR_PATH
                try:
                    user = User.query.filter(User.username == username).first()
                    if user.password != password and session['username'] == username:
                        result['go_login_page'] = True
                        # 删除session
                        session.pop('username', None)
                    else:
                        result['go_login_page'] = False
                    user.password = password
                    user.avatar = avatar
                    user.info = info
                    user.email = email
                    db.session.commit()
                    result['user_edit_status'] = 'success'
                    result['user_info_list'] = Tools.get_user_info_list()
                except Exception, e:
                    result['user_edit_status'] = 'danger'
            else:
                result['user_edit_status'] = 'danger'
    return json.dumps(result)


def check_user(username, password, email, avatar, role, info, type='add'):
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