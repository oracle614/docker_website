from flask import render_template, url_for, redirect, request, session, flash
from apps.tool import ConnectNode
from apps.tool import Event
from apps.import_image import *
from common import *


connect_node = None


# login function
@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if 'username' not in session:
            return render_template('page-login.html')
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
    return redirect(url_for('login'))


# logout function
@app.route('/logout/')
def logout():
    if 'username' in session:
        session.pop('username', None)
    return redirect(url_for('login'))


@app.route('/lockscreen/', methods=['GET', 'POST'])
def lock():
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


@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    elif 'lock_stat' in session:
        return  redirect(url_for('lock'))
    user = User.query.filter(User.username == session['username']).first()
    event_info = Event.get_event(10)
    context = {
        'username': user.username,
        'avatar': user.avatar,
        'role': user.role,
        'cluster_info': connect_node.cluster_info,
        'event_info': event_info
    }
    # Event.write_event('admin', 'load image start', datetime.datetime.now())
    if context.get('avatar') is None:
        context.pop('avatar')
    return render_template('index.html', **context)


def _get_node_info():
    '''

    :return:[(ip, port, username, password, dir),....]
    '''
    nodes = Node.query.filter().all()
    nodes_info = []
    for node in nodes:
        ip = str(node.ip)
        port = int(node.port)
        username = str(node.username)
        password = str(node.password)
        image_dir = str(node.image_dir)
        nodes_info.append((ip, port, username, password, image_dir))
    return nodes_info


if __name__ == '__main__':
    nodes_info = _get_node_info()
    connect_node = ConnectNode(nodes_info)
    connect_node.create_demo()
    db.create_all()
    try:
        app.run(debug=True)
    finally:
        connect_node.close_demo()
        connect_node.close()
