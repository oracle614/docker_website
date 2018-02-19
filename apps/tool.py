# coding=utf-8
import paramiko
import os, threading, datetime, logging, time, sys
import re
reload(sys)
sys.setdefaultencoding('utf8')
sys.path.append('../')
from base import *
from flask import session, redirect, url_for


class ConnectNode(object):
    def __init__(self):
        """
            init connect
        :result nodes format: [[trans object, ssh object, (ip, port, username, password, dir)],....]
        """
        self.demo_status = True
        self.cluster_info = {}
        self.nodes_info = []
        # Is it being updated
        # This value is true when the demo is updating the node information.
        # You need to wait for this value to be False to perform other operations
        self.flush_status = False
        self.nodes = []
        # Is it allowed to update
        # When this value is marked to True, the demo process does not update the node information while the loop waits.
        # When the operation is performed, the value must be set to True and the value is set to False.
        self.bool_flush = True

    def create_demo(self):
        """
            The background process is created to update nodes_info, nodes, and obtain the overall information of the node
        :return: There is no return value
        """
        update_demo = threading.Thread(target=self._update_nodes_demo, name='thread-demo1')
        update_demo.start()

    def _get_node_info(self):
        """
            Get the cluster node information from the database and write it to self.nodes_info
        :return:node_info format: [[ip, port, username, password, dir],....]
        """
        # Get node info from DB
        # 此处使用离线线程运行,即本线程的运行与用户是否请求无关,而如果直接在一个 Flask-SQLAlchemy 写成的 Model 上调用
        # User.query.get(user_id)，就会遇到 RuntimeError。因为此时应用上下文还没被推入栈中，而 Flask-SQLAlchemy
        # 需要数据库连接信息时就会去取 current_app.config，current_app 指向的却是 _app_ctx_stack为空的栈顶。
        # 解决的办法是运行脚本正文之前，先将 App 的 App Context 推入栈中，栈顶不为空后 current_app这个 Local Proxy 对象
        # 就自然能将“取 config 属性” 的动作转发到当前 App 上
        # 引用app应用上下文
        with app.app_context():
            query_nodes = Node.query.filter().all()
            nodes_info = []
            for node in query_nodes:
                ip = str(node.ip)
                port = int(node.port)
                username = str(node.username)
                password = str(node.password)
                image_dir = str(node.image_dir)
                # master_ip = Sys.query.filter().first().master_node
                # if ip == master_ip:
                #     master = True
                # else:
                #     master = False
                # nodes_info.append((ip, port, username, password, image_dir, master))
                nodes_info.append([ip, port, username, password, image_dir])
        # set nodes_info
        self.nodes_info = nodes_info

    def _create_ssh(self):
        """
            Create paramiko connection using the nodes_info table. If the connection is successful, the first two items are
        both trans objects and SSH objects, otherwise None is convenient for subsequent operation.
        :return: nodes format: [[trans, ssh, [ip, port, username, password, dir, bool_master]]...]
        """
        temp = []
        for node_info in self.nodes_info:
            try:
                trans = paramiko.Transport((node_info[0], node_info[1]))
                trans.connect(username=node_info[2], password=node_info[3])
                ssh = paramiko.SSHClient()
                ssh._transport = trans
                # 创建目录
                ssh.exec_command('sudo mkdir -p {dir}'.format(dir=node_info[4]))
            except Exception, e:
                ssh = None
                trans = None
            # 将该节点是否可用信息写入数据库
            with app.app_context():
                query_node = Node.query.filter(Node.ip == node_info[0]).first()
                if ssh is None or trans is None:
                    query_node.available = 'False'
                else:
                    query_node.available = 'True'
                db.session.commit()
            temp.append([trans, ssh, node_info])
        self.nodes = temp

    def _set_master(self):
        """
        选取一个可用节点为主节点
        :return:
        """
        master_ip = Sys.query.filter().first()
        bool_set = False
        if master_ip is not None:
            node_ip = Node.query.filter(Node.ip == master_ip.master_node).first()
            if node_ip is not None:
                # 主节点已设置且主节点ip有效,但本节点不可用
                if node_ip.available != 'True':
                    bool_set = True
                else:
                    pass
            # 主节点已设置但主节点ip无效
            else:
                bool_set = True
        # 主节点未设置
        else:
            bool_set = True
        # 选取一个可用的ip设置为主节点
        if bool_set:
            query_ip = Node.query.filter(Node.available == 'True').first()
            if query_ip is not None:
                ip = query_ip.ip
                master_node = Sys.query.filter().first()
                master_node.master_node = ip
                db.session.commit()
            else:
                query_ip = Node.query.filter().first()
                if query_ip is not None:
                    ip = query_ip.ip
                    master_node = Sys.query.filter().first()
                    master_node.master_node = ip
                    db.session.commit()

    def _update_nodes_info(self):
        """向self.nodes_info中添加主节点信息.
        修改后self.nodes_info格式如下:
            [[ip, port, username, password, dir, bool_master],....]
        由于self.nodes_info与self.nodes[2]位于同块内存地址,故self.nodes更改为如下格式:
            [[trans, ssh, [ip, port, username, password, dir, bool_master]]...]
        :return: 无返回值
        """
        query_master_ip = Sys.query.filter().first()
        if query_master_ip is None:
            return
        master_ip = query_master_ip.master_node
        for index in xrange(len(self.nodes_info)):
            if self.nodes_info[index][0] == master_ip:
                self.nodes_info[index].append(True)
            else:
                self.nodes_info[index].append(False)

    def _update_nodes_demo(self):
        """
            This function is a background daemon, which is used to obtain the number of containers,
        running containers, mirrored files, mirrored files, and node status of each node in the
        cluster and write it to the log / cluster_info.json file as json.
        """
        cmd_all_container = 'docker ps -aq |wc -l'
        cmd_alive_container = 'docker ps -q |wc -l'
        cmd_docker_image = 'docker images -q|wc -l'
        while self.demo_status:
            while not self.bool_flush:
                pass
            self.flush_status = True
            # Update node information.
            self._get_node_info()
            # Update ssh connect.
            self._create_ssh()
            # Set master_node
            self._set_master()
            # Update info
            self._update_nodes_info()
            self.flush_status = False
            try:
                # time.sleep(5)
                cluster_node_num = len(self.nodes)
                cluster_container_num = 0
                cluster_alive_container_num = 0
                cluster_docker_num = 0
                cluster_tar_num = 0
                node_container_num = 0
                node_alive_container_num = 0
                node_docker_num = 0
                node_tar_num = 0
                cluster_info = {}
                result_tar_image = []
                cluster_nodes_info = []
                for node in self.nodes:
                    if node[0] is not None and node[1] is not None:
                        create_tar_image_cmd = 'mkdir -p {dirs}'.format(dirs=node[2][4])
                        cmd_tar_image = 'ls {dirs} |wc -l'.format(dirs=node[2][4])
                        # 创建目录
                        # node[1].exec_commands(create_tar_image_cmd)
                        stdin, stdout, stderr = node[1].exec_command(cmd_tar_image)
                        status = 'success'
                    else:
                        # ssh is default
                        status = 'defeated'
                        stdout, stderr = None, None
                    result_tar_image.append((node[2][0], status, (stdout, stderr)))
                result_all_container = self.cmds(cmd_all_container)
                result_alive_container = self.cmds(cmd_alive_container)
                result_docker_image = self.cmds(cmd_docker_image)
                for index in xrange(len(self.nodes)):
                    # Status is True
                    if result_all_container[index][1] == 'success':
                        try:
                            node_container_num = int(result_all_container[index][2][0].readlines()[0].split('\n')[0])
                            node_alive_container_num = int(result_alive_container[index][2][0].readlines()[0].split('\n')[0])
                            node_docker_num = int(result_docker_image[index][2][0].readlines()[0].split('\n')[0])
                            node_tar_num = int(result_tar_image[index][2][0].readlines()[0].split('\n')[0])
                        except Exception, e:
                            # write log to json
                            # self.logger.error(e.message)
                            pass
                        cluster_container_num += node_container_num
                        cluster_alive_container_num += node_alive_container_num
                        cluster_docker_num += node_docker_num
                        cluster_tar_num += node_tar_num
                    else:
                        node_container_num = 0
                        node_alive_container_num = 0
                        node_docker_num = 0
                        node_tar_num = 0
                    cluster_nodes_info.append(
                        {
                            'index': index+1, 'IP': self.nodes[index][2][0], 'node_container_num': node_container_num,
                            'node_alive_container_num': node_alive_container_num, 'node_docker_num': node_docker_num,
                            'node_tar_num': node_tar_num, 'node_status': str(result_tar_image[index][1])
                        }
                    )
                cluster_info['cluster_container_num'] = cluster_container_num
                cluster_info['cluster_alive_container_num'] = cluster_alive_container_num
                cluster_info['cluster_docker_num'] = cluster_docker_num
                cluster_info['cluster_tar_num'] = cluster_tar_num
                cluster_info['cluster_node_num'] = cluster_node_num
                cluster_info['cluster_flush_time'] = datetime.datetime.strftime(
                    datetime.datetime.now(), '%b %d, %Y  %I:%M:%S %p')
                cluster_info['cluster_nodes_info'] = cluster_nodes_info
                self.cluster_info = cluster_info
                time.sleep(20)
                self.close()
            except Exception, e:
                print e
                self.close()

    def cmd(self, ip, cmd):
        """
        Executes the specified command on the specified node.
        :param ip: format:'10.42.0.74'
        :param cmd: shell cmd
        :return: (ip, status, (stdout, stderr))
        """
        node = self.get_ip_attr(ip, 'info')
        if node[0] is not None and node[1] is not None:
            try:
                _, stdout, stderr = node[1].exec_command(cmd)
                status = 'success'
            except Exception, e:
                status = 'defeated'
                stdout, stderr = None, None
        else:
            status = 'defeated'
            stdout, stderr = None, None
        return node[2][0], status, (stdout, stderr)

    def cmds(self, cmd):
        """
        Perform the same command on all nodes.
        :param cmd: shell cmd
        :return: [(ip, status, (stdin, stderr))]
        """
        end = []
        nodes = self.nodes
        for node in nodes:
            ip = node[2][0]
            temp = self.cmd(ip, cmd)
            status = temp[1]
            result = temp[2]
            end.append((ip, status, result))
        return end

    def get_ip_list(self, master=True, available=True):
        """
        Returns the IP list. By default, the master node is displayed and the node is not displayed
        :param master: Does it return to the master node
        :return:[ip1, ip2, ip3]
        """
        self.bool_flush = False
        while self.flush_status:
            pass
        result = []
        for ip in self.nodes:
            if not master:
                if ip[2][5]:
                    continue
            if available:
                if ip[0] is None or ip[1] is None:
                    continue
            result.append(ip[2][0])
        self.bool_flush = True
        return result

    def get_ip_attr(self, ip, attr):
        """
        Returns information about the specified IP, and None if the IP does not exist in the database.
        :param ip: str; eg:'10.42.0.74'
        :param attr: key values
        :return: node info
        """
        index = 0
        for node in self.nodes:
            if node[2][0] == ip:
                if attr == 'dir':
                    return node[2][4]
                elif attr == 'port':
                    return node[2][1]
                elif attr == 'username':
                    return node[2][2]
                elif attr == 'password':
                    return node[2][3]
                elif attr == 'master':
                    return node[2][5]
                elif attr == 'trans':
                    return node[0]
                elif attr == 'ssh':
                    return node[1]
                elif attr == 'index':
                    return index
                elif attr == 'info':
                    return node
            index += 1
        else:
            return None

    def close_demo(self):
        """
        Close the background daemon.
        :return: There is no return value.
        """
        self.demo_status = False
        self.bool_flush = True

    def close(self):
        """
        Close all paramiko connections.
        :return: There is no return value.
        """
        nodes = self.nodes
        for node in nodes:
            if node[0] is not None or node[1] is not None:
                node[0].close()
                node[1].close()


class Event(object):
    """
    Package the event operation as an API
    """

    @staticmethod
    def write_event(username, event, date):
        """
        Writes the event to the database.
        :param username: The username of the event executor
        :param event: The contents of what happened
        :param date: When did it happen.It is a python datetime object
        :return: None
        """
        date = date.strftime('%Y-%m-%d %H:%M:%S')
        avatar = User.query.filter(User.username == username).first().avatar
        if avatar is None:
            avatar = url_for('static', filename='img/user1.png')
        event = EventInfo(username=username, avatar=avatar, date=date, event=event)
        db.session.add(event)
        db.session.commit()

    @staticmethod
    def get_event(num):
        """
        Package the latest number of events.
        :param num: Package the latest number of events
        :return: Events in the dictionary. format: [{'username': '',avatar': '','date': '','event_info': ''}, ......]
        """
        events = EventInfo.query.order_by(db.desc(EventInfo.date)).limit(num)
        events_to_list = []
        for event in events:
            date_before = datetime.datetime.strptime(str(event.date), '%Y-%m-%d %H:%M:%S')
            date_now = datetime.datetime.now()
            date_delta = date_now - date_before
            # eg: 1 months ago
            if date_delta.days > 30:
                date = '%d months ago' % (date_delta.days/30)
            # eg: 24 days ago
            elif date_delta.days >= 2:
                date = '%d days ago' % date_delta.days
            # eg: Yesterday
            elif date_delta.days >= 1:
                date = 'Yesterday'
            # eg: 5 hours ago
            elif date_delta.seconds > 60 * 60:
                date = '%d hours ago' % (date_delta.seconds / 3600)
            # eg: 30 minutes ago
            elif date_delta.seconds > 60:
                date = '%d minutes ago' % (date_delta.seconds / 60)
            # eg: 49 seconds ago
            else:
                date = '%d seconds ago' % date_delta.seconds
            temp = {
                'username': event.username,
                'avatar': event.avatar,
                'event_info': event.event,
                'date': date
            }
            if temp.get('avatar') is None:
                temp.pop('avatar')
            events_to_list.append(temp)
        return events_to_list


class Message(object):
    """
    Manage the current user's message.
    """
    @staticmethod
    def write_message(info, username, grade='success'):
        """
        向数据库中写入消息
        :param info:消息内容
        :param username: 消息的属主
        :param grade: 消息等级.success or danger
        :return:
        """
        date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        info = datetime.datetime.now().strftime('%H:%M:%S') + ': ' + info
        message = MessageInfo(info=info, username=username, grade=grade, date=date, status='false')
        db.session.add(message)
        db.session.commit()

    @staticmethod
    def get_message(username, max_num):
        """
        获取新消息
        :param username: 用户名
        :param max_num: 如果num大于未读消息数,则仅返回新消息数;否则返回num个数新消息
        :return: [{'info': ,''grade: ,'message_id': , 'message_status'}, {}]
        """
        messages = MessageInfo.query.filter(MessageInfo.username == username).filter(MessageInfo.status == 'false').order_by(db.desc(MessageInfo.date)).limit(max_num)
        messages_to_list = []
        for message in messages:
            messages_to_list.append({'info': message.info, 'grade': message.grade, 'message_id': int(message.message_id), 'message_status': message.status})
        return messages_to_list

    @staticmethod
    def mark_true(username, message_ids):
        """
        标记ids的消息为已读
        :param username:
        :param message_ids: 消息id列表
        :return:
        """
        for id in message_ids:
            message = MessageInfo.query.filter(MessageInfo.message_id == id).first()
            message.status = 'true'
        db.session.commit()


# Declare connect_node for other class access.
connect_node = None


def init():
    """
        Initializes the ConnectNode object and creates the background daemon to update the information. This method runs
    only once during service operation.
    :return: There is no return value.
    """
    global connect_node
    connect_node = ConnectNode()
    connect_node.create_demo()


class Tools(object):
    @staticmethod
    def state_judgment():
        """
        !!! This feature may be deprecated.!!!
        Determine the user status and jump to the relevant page.
        :return: There is no return value.
        """
        if 'username' not in session:
            redirect(url_for('login'))
        elif 'stat_lock' in session:
            redirect(url_for('lock'))

    @staticmethod
    def get_user_set():
        """
        返回用户信息
        :return:
        """
    @staticmethod
    def set_ip_master(available=False):
        """
        设置主节点
        :param available: True表示不设置不可用节点为主节点,False表示可设置不可用节点为主节点
        :return:
        """
        master_ip = Sys.query.filter().first()
        bool_set = False
        if master_ip is not None:
            node_ip = Node.query.filter(Node.ip == master_ip).first()
            if node_ip is not None:
                if available:
                    # 主节点已设置且主节点ip有效,但本节点不可用
                    if node_ip.available != 'True':
                        bool_set = True
                    else:
                        pass
            # 主节点已设置但主节点ip无效
            else:
                bool_set = True
        # 主节点未设置
        else:
            bool_set = True
        # 选取一个可用的ip设置为主节点
        if bool_set:
            if available:
                ip = Node.query.filter(Node.available == 'True').first().ip
            else:
                ip = Node.query.filter().first().ip
            master_node = Sys(master_node=ip)
            db.session.add(master_node)
            db.session.commit()

    @staticmethod
    def get_connect_node():
        """
            Returns the global variable connect_node to facilitate access to the connection object instance at other
        nodes.This instance contains a series of cluster operation functions.
        :return: ConnectNode obj
        """
        global connect_node
        return connect_node

    @staticmethod
    def get_ip_list(master=True, available=True):
        """返回ip列表.默认返回主节点及可用节点
        :param available: 是否返回不可用节点.`True`表示仅返回可用节点.`False`表示返回所有节点
        :param master: 是否返回主节点.`True`表示返回主节点ip,`False`表示返回所有节点
        :return:[ip1, ip2, ip3]
        """
        connect_node = Tools.get_connect_node()
        connect_node.bool_flush = False
        while connect_node.flush_status:
            pass
        result = []
        for ip in connect_node.nodes:
            if not master:
                if ip[2][5]:
                    continue
            if available:
                if ip[0] is None or ip[1] is None:
                    continue
            result.append(ip[2][0])
        connect_node.bool_flush = True
        return result

    @staticmethod
    def get_image_file_list(ip, recent_time=False):
        """获取指定ip的镜像文件信息列表.
        :param recent_time: 是否返回最近时间
        :param ip: ip str,eg:10.42.0.74
        :return:[[id, filename, create_time[,change_time], file_size],...]
        """
        connect = Tools.get_connect_node()
        info = []
        #
        connect.bool_flush = False
        while connect.flush_status:
            pass
        ip_dir = connect.get_ip_attr(ip, 'dir')
        node = connect.get_ip_attr(ip, 'info')
        cmd = 'ls {ip_dir}'.format(ip_dir=ip_dir)
        exec_result = connect.cmd(ip, cmd)
        if exec_result[1] == 'success':
            filess = exec_result[2][0].readlines()
            ids = 0
            for files in filess:
                ids += 1
                files = files.split('\n')[0]
                change_time = Tools._get_change_file_time(node, files)
                file_size = Tools._get_file_size(node, files)
                create_time = Tools._get_create_file_time(node, files)
                if recent_time:
                    info.append([ids, files, create_time, change_time, file_size])
                else:
                    info.append([ids, files, create_time, file_size])
        connect.bool_flush = True
        return info

    @staticmethod
    def get_docker_image_list(ip, status=False):
        """返回Docker镜像列表
        :param status: 是否返回镜像状态.`True`表示返回,`False`表示不返回
        :param ip: ip str,eg:10.42.0.74
        :return: [[Id, image_name, imageId, created, size， tag]]
        """
        connect = Tools.get_connect_node()
        info = []
        connect.bool_flush = False
        while connect.flush_status:
            pass
        cmd = 'docker images |grep -v TAG'
        exec_result = connect.cmd(ip, cmd)
        pattern = r'(\S+)\s*(\S+)\s*(\S+)\s*(\d+ \S+ \S+)\s+(.*)'
        com = re.compile(pattern)
        if exec_result[1] == 'success':
            imagess = exec_result[2][0].readlines()
            ids = 0
            for images in imagess:
                ids += 1
                images = images.split('\n')[0]
                re_result = re.match(com, images)
                image_name = re_result.group(1)
                tag = re_result.group(2)
                image_id = re_result.group(3)
                created = re_result.group(4)
                size = re_result.group(5)
                if status is True:
                    container_image_list = Tools._get_container_image(ip)
                    complex_images = image_name + ':' + tag
                    if complex_images in container_image_list:
                        image_status = 'Using'
                    else:
                        image_status = 'NoUse'
                    info.append([ids, image_name, image_id, created, size, tag, image_status])
                else:
                    info.append([ids, image_name, image_id, created, size, tag])
        connect.bool_flush = True
        return info

    @staticmethod
    def get_user_info_list():
        """返回用户信息列表
        # 顺序 id-用户名-密码-邮箱-创建日期-角色-简介
        :return: [[id, username, password, email, create_time, role, info], ...]
        """
        users = User.query.filter().all()
        info = []
        ids = 0
        for user in users:
            ids += 1
            info.append([ids, user.username, user.password, user.email, user.createtime.strftime('%Y-%m-%d %H:%M:%S'),
                         user.role, user.info])
        return info

    @staticmethod
    def get_sys_info_list():
        """返回本集群系统信息
        # 顺序 id-ip-端口-账户-密码-镜像文件位置-是否是主节点
        :return:
        """
        sys_infos = Node.query.filter().all()
        info = []
        ids = 0
        for sys_info in sys_infos:
            ids += 1
            bool_master = Tools.get_connect_node().get_ip_attr(sys_info.ip, 'master')
            info.append([ids, sys_info.ip, int(sys_info.port), sys_info.username,
                         sys_info.password, sys_info.image_dir, bool_master])
        return info

    @staticmethod
    def _get_container_image(ip):
        """返回该节点所有容器依赖的镜像
        基本思路：
        1. 通过docker ps -a命令返回所有容器所用的镜像
        2. 处理镜像名：若获取的镜像名包含版本号,不处理;若获取的镜像名不包含版本号,则在该镜像名后添加`:latest`标签
        3. 将处理完成的容器镜像名列表返回
        :param ip: 操作节点IP
        :return: 镜像名列表[镜像名1...]
        """
        connect = Tools.get_connect_node()
        cmd = "docker ps -a|grep -v IMAGE|awk '{print $2}'"
        # 获取所有容器镜像
        exec_result = connect.cmd(ip, cmd)
        container_image_list = []
        if exec_result[1] == 'success':
            container_images = exec_result[2][0].readlines()
            for container_image in container_images:
                container_image = container_image.split('\n')[0]
                # 逐个处理
                if ':' not in container_image:
                    container_image += ':latest'
                container_image_list.append(container_image)
        return container_image_list

    @staticmethod
    def _get_change_file_time(node, filename):
        """
        Returns the change date of the specified file under the mirror folder directory in the specified node.
        :param node: [trans, ssh, (......)] same as self.nodes[0]
        :param filename: file name
        :return: file_time(str)
        """
        connect = Tools.get_connect_node()
        path = node[2][4] + '/' + filename
        cmd = 'ls --full-time {path}|cut -d " " -f 6,7|cut -d "." -f 1'.format(path=path)
        result = connect.cmd(node[2][0], cmd)
        file_time = None
        if result[1] == 'success':
            file_time = result[2][0].readlines()[0].split('\n')[0]
        return file_time

    @staticmethod
    def _get_create_file_time(node, filename):
        """
        Returns the create date of the mirrored file under the mirror folder directory in the specified node.
        :param node:[trans, ssh, (......)] same as self.nodes[0]
        :param filename:file name
        :return: file recent
        """
        connect = Tools.get_connect_node()
        path = node[2][4] + '/' + filename
        cmd = 'stat {path}|grep Access |grep + |cut -d " " -f 2,3|cut -d "." -f 1'.format(path=path)
        result = connect.cmd(node[2][0], cmd)
        file_recent_time = None
        if result[1] == 'success':
            file_recent_time = result[2][0].readlines()[0].split('\n')[0]
        return file_recent_time

    @staticmethod
    def _get_file_size(node, filename):
        """
        Returns the size of the specified file in the image folder directory in the specified node.
        :param node: [trans, ssh, (......)] same as self.nodes[0]
        :param filename: file name
        :return:
        """
        connect = Tools.get_connect_node()
        path = node[2][4] + '/' + filename
        cmd = 'ls -lht {path}|cut -d " " -f 5'.format(path=path)
        result = connect.cmd(node[2][0], cmd)
        file_size = None
        if result[1] == 'success':
            file_size = result[2][0].readlines()[0].split('\n')[0]
        return file_size