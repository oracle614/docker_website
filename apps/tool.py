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
        :param nodes_info:format:[(ip, port, username, password, dir),....]
        :result nodes format: [[trans object, ssh object, (ip, port, username, password, dir)],....]
        """
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.ERROR)
        headler = logging.FileHandler('log/error.log')
        headler.setLevel(logging.ERROR)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        headler.setFormatter(formatter)
        self.logger.addHandler(headler)
        self.demo_status = True
        self.cluster_info = {}
        self.nodes_info = []
        # Is it being updated
        # This value is true when the demo is updating the node information.
        # You need to wait for this value to be False to perform other operations
        self.flush_status = False
        # Is it allowed to update
        # When this value is marked to True, the demo process does not update the node information while the loop waits.
        # When the operation is performed, the value must be set to True and the value is set to False.
        self.bool_flush = True

    def create_demo(self):
        """
            The background process is created to update nodes_info, nodes, and obtain the overall information of the node
        :return: There is no return value
        """
        if not os.path.exists('log'):
            os.makedirs('log')
        demo1 = threading.Thread(target=self._demo, name='thread-demo1')
        demo1.start()

    def _get_node_info(self):
        """
            Get the cluster node information from the database and write it to self.nodes_info
        :return:node_info format: [(ip, port, username, password, dir, master),....]
        """
        # get node info from DB
        nodes = Node.query.filter().all()
        nodes_info = []
        for node in nodes:
            ip = str(node.ip)
            port = int(node.port)
            username = str(node.username)
            password = str(node.password)
            image_dir = str(node.image_dir)
            master_ip = Sys.query.filter().first().master_node
            if ip == master_ip:
                master = True
            else:
                master = False
            nodes_info.append((ip, port, username, password, image_dir, master))
        # set nodes_info
        self.nodes_info = nodes_info

    def _create_ssh(self):
        """
            Create paramiko connection using the nodes_info table. If the connection is successful, the first two items are
        both trans objects and SSH objects, otherwise None is convenient for subsequent operation.
        :return: nodes format: [[trans, ssh, (ip, port, username, password, dir, master)]...]
        """
        temp = []
        for node_info in self.nodes_info:
            try:
                trans = paramiko.Transport((node_info[0], node_info[1]))
                trans.connect(username=node_info[2], password=node_info[3])
                ssh = paramiko.SSHClient()
                ssh._transport = trans
            except Exception, e:
                ssh = None
                trans = None
            temp.append([trans, ssh, node_info])
        self.nodes = temp

    def _demo(self):
        """
            This function is a background daemon, which is used to obtain the number of containers,
        running containers, mirrored files, mirrored files, and node status of each node in the
        cluster and write it to the log / cluster_info.json file as json.
        """
        cmd_all_container = 'docker ps -a |wc -l'
        cmd_alive_container = 'docker ps|wc -l'
        cmd_docker_image = 'docker images|wc -l'
        while self.demo_status:
            while not self.bool_flush:
                pass
            self.flush_status = True
            # Update node information.
            self._get_node_info()
            # Update ssh connect.
            self._create_ssh()
            self.flush_status = False
            try:
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
                # Each node has its own file directory. Unable to perform batch operations.
                for node in self.nodes:
                    if node[0] is not None and node[1] is not None:
                        cmd_tar_image = 'ls {dirs} |wc -l'.format(dirs=node[2][4])
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
                            self.logger.error(e.message)
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
                    datetime.datetime.now(), '%b %d, %Y  %I:%M %p')
                cluster_info['cluster_nodes_info'] = cluster_nodes_info
                # print cluster_info
                self.cluster_info = cluster_info
                time.sleep(20)
                self.close()
                print '新循环开始'
            except Exception, e:
                print e
                self.close()

    def cmd(self, node, cmd):
        """
        Executes the specified command on the specified node.
        :param node: format:[trans, ssh, (ip, port, username, password, dir, master)]
        :param cmd: shell cmd
        :return: (ip, status, (stdout, stderr))
        """
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
            temp = self.cmd(node, cmd)
            status = temp[1]
            result = temp[2]
            end.append((node[2][0], status, result))
        return end

    def get_image_file_list(self, ip, recent_time=False):
        """
        Gets the image file information in the specified IP node.
        :param ip: ip str,eg:10.42.0.74
        :return:[[id, filename, create_time[,change_time], file_size],...]
        """
        info = []
        #
        self.bool_flush = False
        while self.flush_status:
            pass
        ip_dir = self.get_ip_attr(ip, 'dir')
        node = self.get_ip_attr(ip, 'info')
        cmd = 'ls {ip_dir}'.format(ip_dir=ip_dir)
        exec_result = self.cmd(node, cmd)
        if exec_result[1] == 'success':
            filess = exec_result[2][0].readlines()
            ids = 0
            for files in filess:
                ids += 1
                files = files.split('\n')[0]
                change_time = self._get_change_file_time(node, files)
                file_size = self._get_file_size(node, files)
                create_time = self._get_create_file_time(node, files)
                if recent_time:
                    info.append([ids, files, create_time, change_time, file_size])
                else:
                    info.append([ids, files, create_time, file_size])
        self.bool_flush = True
        return info

    def get_docker_image_list(self, ip):
        """
        Get the docker mirror list.
        :param ip: ip str,eg:10.42.0.74
        :return: [[Id, image_name, imageId, created, size， tag]]
        """
        info = []
        self.bool_flush = False
        while self.flush_status:
            pass
        node = self.get_ip_attr(ip, 'info')
        cmd = 'docker images |grep -v TAG'
        exec_result = self.cmd(node, cmd)
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
                info.append([ids, image_name, image_id, created, size, tag])
        print info
        self.bool_flush = True
        return info

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

    def _get_change_file_time(self, node, filename):
        """
        Returns the change date of the specified file under the mirror folder directory in the specified node.
        :param node: [trans, ssh, (......)] same as self.nodes[0]
        :param filename: file name
        :return: file_time(str)
        """
        path = node[2][4] + '/' + filename
        cmd = 'ls --full-time {path}|cut -d " " -f 6,7|cut -d "." -f 1'.format(path=path)
        result = self.cmd(node, cmd)
        file_time = None
        if result[1] == 'success':
            file_time = result[2][0].readlines()[0].split('\n')[0]
        return file_time

    def _get_create_file_time(self, node, filename):
        """
        Returns the create date of the mirrored file under the mirror folder directory in the specified node.
        :param node:[trans, ssh, (......)] same as self.nodes[0]
        :param filename:file name
        :return: file recent
        """
        path = node[2][4] + '/' + filename
        cmd = 'stat {path}|grep Access |grep + |cut -d " " -f 2,3|cut -d "." -f 1'.format(path=path)
        result = self.cmd(node, cmd)
        file_recent_time = None
        if result[1] == 'success':
            file_recent_time = result[2][0].readlines()[0].split('\n')[0]
        return file_recent_time

    def _get_file_size(self, node, filename):
        """
        Returns the size of the specified file in the image folder directory in the specified node.
        :param node: [trans, ssh, (......)] same as self.nodes[0]
        :param filename: file name
        :return:
        """
        path = node[2][4] + '/' + filename
        cmd = 'ls -lht {path}|cut -d " " -f 5'.format(path=path)
        result = self.cmd(node, cmd)
        file_size = None
        if result[1] == 'success':
            file_size = result[2][0].readlines()[0].split('\n')[0]
        return file_size

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
        Writes the message to the database.
        :param info:
        :param username:
        :param grade: success or danger
        :return:
        """
        date = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        info = datetime.datetime.now().strftime('%H:%M:%S') + ': ' + info
        message = MessageInfo(info=info, username=username, grade=grade, date=date)
        db.session.add(message)
        db.session.commit()

    @staticmethod
    def get_message(username, num):
        """
        Gets the user username recently the num bar message.
        :param username:
        :param num:
        :return: [{'info': ,''grade: ,'message_id': }, {}]
        """
        messages = MessageInfo.query.filter(MessageInfo.username == username).order_by(db.desc(MessageInfo.date)).limit(num)
        messages_to_list = []
        for message in messages:
            messages_to_list.append({'info': message.info, 'grade': message.grade, 'message_id': int(message.message_id)})
        return messages_to_list


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
    def get_connect_node():
        """
            Returns the global variable connect_node to facilitate access to the connection object instance at other
        nodes.This instance contains a series of cluster operation functions.
        :return: ConnectNode obj
        """
        global connect_node
        return connect_node