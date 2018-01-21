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
            if check_user(username=username, password=password, email=email, avatar=avatar, role=role, info=info):
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
            print result
        elif received.get('type') == 'user_info':
            # 顺序 id-用户名-密码-邮箱-创建日期-角色-简介
            users_list = Tools.get_user_info_list()
            result['user_info_status'] = 'success'
            result['user_info_list'] = users_list
            print result
    return json.dumps(result)


def check_user(username, password, email, avatar, role, info):
    """检测账户相关属性是否合法
    :param username: 用户名
    :param password: 密码
    :param email: 邮箱
    :param avatar: 头像
    :param role: 角色
    :param info: 简介
    :return: Bool值,`True`表示通过检测,`False`表示未通过检测
    """
    if len(username) > 10 or len(password) > 16 or len(password) < 0 or len(username) < 0 \
            or len(role) == 0 \
            or len(email) > 50 \
            or len(avatar) > 300:
        return False
    if role != 'ordinary' and role != 'warden':
        return False
    # 检测本账户是否已存在
    user = User.query.filter(User.username == username).first()
    # 帐号存在
    if user is not None:
        return False
    return True