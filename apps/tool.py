# coding=utf-8
import paramiko
import os, threading, datetime, logging, time, sys
sys.path.append('../')
from common import *
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
        # self.nodes_info = nodes_info
        # assert isinstance(nodes_info, list)
        # for node_info in nodes_info:
        #     assert isinstance(node_info[1], int)
        #     try:
        #         trans = paramiko.Transport((node_info[0], node_info[1]))
        #         trans.connect(username=node_info[2], password=node_info[3])
        #         ssh = paramiko.SSHClient()
        #         ssh._transport = trans
        #     except:
        #         ssh = None
        #         trans = None
        #     self.nodes.append([trans, ssh, node_info])

    def create_demo(self):
        # Create a background process to monitor the status of the cluster.
        if not os.path.exists('log'):
            os.makedirs('log')
        # demo2 = threading.Thread(target=self._create_ssh, name='thread-demo2')
        demo1 = threading.Thread(target=self._demo, name='thread-demo1')
        # demo3 = threading.Thread(target=self._get_node_info, name='thread-demo3')
        # demo3.start()
        # time.sleep(1)
        # demo2.start()
        # time.sleep(2)
        demo1.start()

    def _get_node_info(self):
        """
        set nodes_info
        :return:node_info format: [(ip, port, username, password, dir, master),....]
        """
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
        set self.nodes
        :return: format: [[trans, ssh, (ip, port, username, password, dir, master)]...]
        """
        self.nodes = []
        for node_info in self.nodes_info:
            try:
                # print node_info
                trans = paramiko.Transport((node_info[0], node_info[1]))
                trans.connect(username=node_info[2], password=node_info[3])
                ssh = paramiko.SSHClient()
                ssh._transport = trans
            except Exception, e:
                ssh = None
                trans = None
            self.nodes.append([trans, ssh, node_info])

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
            self._get_node_info()
            self._create_ssh()
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
                # Each node has a different folder path.
                # print self.nodes
                for node in self.nodes:
                    if node[0] is not None and node[1] is not None:
                        cmd_tar_image = 'ls {dirs} |wc -l'.format(dirs=node[2][4])
                        stdin, stdout, stderr = node[1].exec_command(cmd_tar_image)
                        status = 'success'
                    else:
                        # print 'waht'
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
                        except Exception,e:
                            # pass
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
                time.sleep(1)
                self.close()
            except:
                self.close()

    def cmds(self, cmd):
        """
        exec cmd on all node
        :param cmd: shell cmd
        :return: [(ip, status, (stdin, stderr))]
        """
        end = []
        for node in self.nodes:
            temp = self.cmd(node, cmd)
            status = temp[1]
            result = temp[2]
            end.append((node[2][0], status, result))
        return end

    def cmd(self, node, cmd):
        """
        exec cmd on a node
        :param node: format:[trans, ssh, (ip, port, username, password, dir, master)]
        :param cmd: shell cmd
        :return: (ip, status, (stdout, stderr))
        """
        if node[0] is not None and node[1] is not None:
            stdin, stdout, stderr = node[1].exec_command(cmd)
            status = 'success'
        else:
            status = 'defeated'
            stdout, stderr = None, None
        return node[2][0], status, (stdout, stderr)

    def get_image_file_list(self, ip):
        """
        Gets the list of mirrored tar files for the specified node, and then
        :param ip: ip str,eg:10.42.0.74
        :return:[[id, filename, create_time, file_size],...]
        """
        info = []
        ip_dir = self._get_ip_attr(ip, 'dir')
        node = self._get_ip_attr(ip, 'info')
        cmd = 'ls {ip_dir}'.format(ip_dir=ip_dir)
        exec_result = self.cmd(node, cmd)
        if exec_result[1] == 'success':
            filess = exec_result[2][0].readlines()
            ids = 0
            for files in filess:
                ids += 1
                files = files.split('\n')[0]
                create_time = self._get_file_time(node, files)
                file_size = self._get_file_size(node, files)
                info.append([ids, files, create_time, file_size])
        print info
        return info

    def get_docker_image_list(self, ip):
        pass

    def _get_ip_attr(self, ip, attr):
        """
        information from self.nodes
        :param ip:
        :param attr:
        :return:
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

    def _get_file_time(self, node, filename):
        """

        :param node:
        :param filename:
        :return:
        """
        filepath = node[2][4] + '/' + filename
        cmd = 'ls --full-time {filepath}|cut -d " " -f 6,7|cut -d "." -f 1'.format(filepath=filepath)
        time = self.cmd(node, cmd)[2][0].readlines()[0].split('\n')[0]
        return time

    def _get_file_size(self, node, filename):
        filepath = node[2][4] + '/' + filename
        cmd = 'ls -lht {filepath}|cut -d " " -f 5'.format(filepath=filepath)
        temp = self.cmd(node, cmd)[2][0].readlines()[0].split('\n')[0]
        print temp
        return temp

    def close_demo(self):
        self.demo_status = False

    def close(self):
        for node in self.nodes:
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
        :param username:The username of the event executor
        :param event:The contents of what happened
        :param date:When did it happen
        :return: None
        """
        date = date.strftime('%Y-%m-%d %H:%M:%S')
        avatar = User.query.filter(User.username == username).first().avatar
        event = EventInfo(username=username, avatar=avatar, date=date, event=event)
        db.session.add(event)
        db.session.commit()

    @staticmethod
    def get_event(num):
        """
        Package the latest number of events
        :param num: Package the latest number of events
        :return: Events in the dictionary [{'username': ,avatar': ,'date': ,'event_info':  }, ......]
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


connect_node = None


def init():
    global connect_node
    connect_node = ConnectNode()
    connect_node.create_demo()


class Tools(object):
    @staticmethod
    def state_judgment():
        if 'username' not in session:
            redirect(url_for('login'))
        elif 'stat_lock' in session:
            redirect(url_for('lock'))

    @staticmethod
    def get_ip_list():
        temp = Node.quary.filter().all()
        ip_list = []
        for ip in temp:
            ip_list.append(ip.ip)

    @staticmethod
    def get_connect_node():
        global connect_node
        return connect_node