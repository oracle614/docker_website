#!coding:utf-8
import sys
reload(sys)
sys.setdefaultencoding('utf8')
from flask import render_template, url_for, redirect, request, session, flash
from apps.tool import ConnectNode
from apps.tool import Event
from apps.import_ import *
from apps.export import *
from apps.load import *
from apps.rm import *
from apps.show import *
from apps.index import *
from apps.pack import *
from base import *
from apps.tool import *
from apps.common import *
from config import MESSAGE_NUMBER


@app.route('/get/more/')
def get_more():
    return render_template('test_more.html')


@app.route('/head/user/', methods=['POST'])
def get_head_user_info():
    """
    Gets the title bar user information
    :return:{'username': '','avatar': ''}
    """
    user_info = None
    if 'username' not in session:
        return json.dumps({})
    temp = User.query.filter(User.username == session['username']).first()
    user_info = {'username': temp.username, 'avatar': temp.avatar, 'role': temp.role}
    return json.dumps(user_info)


@app.route('/head/message/', methods=['POST'])
def get_message_info():
    """
    响应前台请求
    前端返回{'read_status': values, 'ids': []} values值为bool型 ids值为已读消息编号
    :return: 登录时返回:{'content': [{'info': ,''grade: ,'message_id': , 'message_status'}, {}], 'status': '', 'new_number': ''}; else: {}
    """
    if 'username' in session:
        request_info = request.get_json()
        read_status = request_info.get('read_status')
        ids = request_info.get('ids')
        if read_status:
            # 标记为已读
            Message.mark_true(session['username'], ids)
        username = session['username']
        messages = Message.get_message(username, MESSAGE_NUMBER)
        # Message id, to identify whether there is new message.
        messages_id = [str(message['message_id']) for message in messages]
        messages_id.sort()
        if 'messages_id' in session:
            # Messages_id same as 1_3_4
            session_messages_id = session['messages_id'].split('_')
            session_messages_id.sort()
            if session_messages_id == messages_id or len(messages_id) < len(session_messages_id):
                status = 'old'
                new_number = 0
            else:
                status = 'new'
                common_number = len(set(messages_id) & set(session_messages_id))
                new_number = len(messages_id) - common_number
        else:
            if len(messages_id) != 0:
                status = 'new'
                new_number = len(messages_id)
            else:
                status = 'old'
                new_number = 0
        info = {'content': messages, 'status': status, 'new_number': new_number}
        session['messages_id'] = '_'.join(messages_id)
    else:
        info = {}
    return json.dumps(info)


@app.route('/user/')
def user_set():
    return render_template('user-set.html')


@app.route('/sys/')
def sys_set():
    return render_template('sys-set.html')


# login function
@app.route('/login/', methods=['GET', 'POST'])
def login():
    """
    Handle login requests.
    :return: Flask response.
    """
    if request.method == 'GET':
        if 'username' not in session:
            return render_template('page-login.html', login_err=False)
        elif 'lock_stat' in session:
            return redirect(url_for('lock'))
        else:
            return redirect(url_for('index'))
    else:
        user = User.query.filter(User.username == request.form['username']).first()
        if user is not None:
            if request.form['password'] != user.password:
                error = 'username or password error'
            else:
                session['username'] = user.username
                flash('login sucess')
                return redirect(url_for('index'))
        else:
            error = 'user is not found'
    flash(error)
    # return redirect(url_for('login'))
    return render_template('page-login.html', login_err=True, username=request.form['username'])


# logout function
@app.route('/logout/')
def logout():
    """
    Handle logout requests.
    :return: Flask response.
    """
    if 'username' in session:
        session.pop('username', None)
        if 'messages_id' in session:
            session.pop('messages_id', None)
    return redirect(url_for('login'))


@app.route('/lockscreen/', methods=['GET', 'POST'])
def lock():
    """
    Handle lock requests.
    :return: Flask requests.
    """
    if request.method == 'GET':
        session['lock_stat'] = True
        if 'username' in session:
            user = User.query.filter(User.username == session['username']).first()
            context = {
                'username': user.username,
                'avatar': user.avatar
            }
            if context.get('avatar') is None:
                context.pop('avatar')
            return render_template('page-lockscreen.html', **context)
        else:
            return redirect(url_for('login'))
    else:
        user = User.query.filter(User.username == session['username']).first()
        password = request.form['password']
        if user.password == password:
            session.pop('lock_stat')
            return redirect(url_for('index'))
        else:
            return redirect(url_for('lock'))


# def _get_node_info():
#     '''
#
#     :return:[(ip, port, username, password, dir),....]
#     '''
#     nodes = Node.query.filter().all()
#     nodes_info = []
#     for node in nodes:
#         ip = str(node.ip)
#         port = int(node.port)
#         username = str(node.username)
#         password = str(node.password)
#         image_dir = str(node.image_dir)
#         nodes_info.append((ip, port, username, password, image_dir))
#     return nodes_info


if __name__ == '__main__':
    init()
    try:
        app.run(debug=True, host='0.0.0.0')
    finally:
        Tools.get_connect_node().close_demo()
        Tools.get_connect_node().close()
