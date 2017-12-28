#!coding:utf-8
# common function
import sys
import json
from tool import Tools
from flask import request, session
sys.path.append('../')
from base import *


@app.route('/common/info/', methods=['POST'])
def get_common_info():
    received = request.get_json()
    info = {}
    if received.get('type') == 'node_list':
        if 'username' in session:
            user_role = User.query.filter(User.username == session.get('username')).first().role
            master = received.get('master')
            available = received.get('available')
            # Only when the current user's role is warden, the IP address of the master node will be displayed in the
            # previous section.
            if user_role == 'warden' and master:
                info['node_list'] = Tools.get_connect_node().get_ip_list(master=True, available=available)
            else:
                info['node_list'] = Tools.get_connect_node().get_ip_list(master=False, available=available)
    elif received.get('type') == 'image_file_list':
        if 'username' in session:
            recent_time = received.get('recent_time')
            node = received.get('node')
            info['image_file_list'] = Tools.get_connect_node().get_image_file_list(node, recent_time=recent_time)
    return json.dumps(info)