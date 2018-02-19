#!coding:utf-8
import os

# dialect+driver://username:password@host:port/database
DIALECT = 'mysql'
DRIVER = 'mysqldb'
USERNAME = 'root'
PASSWORD = '123'
PORT = '3306'
HOST = '127.0.0.1'
DATABASE = 'website'

SQLALCHEMY_DATABASE_URI = '{}+{}://{}:{}@{}:{}/{}?charset=utf8'.format(DIALECT, DRIVER, USERNAME, PASSWORD, HOST, PORT, DATABASE)

SQLALCHEMY_TRACK_MODIFICATIONS = False

# CSRF SET
CSRF_ENABLED = True
SECRET_KEY = os.urandom(24)

UPLOAD_FOLDER = os.path.dirname(os.path.abspath('__file__')) + '/' + 'upload'
DOWNLOAD_FOLDER = os.path.dirname(os.path.abspath('__file__')) + '/' + 'download'
TEMP_FOLDER = os.path.dirname(os.path.abspath('__file__')) + '/' + 'temp'
HOME_FOLDER = os.path.dirname(os.path.abspath('__file__'))
NODE_TMP_FOLDER = '/tmp/'
NODE_TMP_IMAGE_FOLDER = '/tmp/dockerImage'

MESSAGE_NUMBER = 5
EVENT_NUMBER = 10

DEFAULT_AVATAR_PATH = '/static/img/user1.png'
DEFAULT_IMAGE_FILE_PATH = '/home/pirate/dockerImage'
DEFAULT_NODE_ACCOUNT = 'pirate'
DEFAULT_NODE_PASSWORD = 'hypriot'
DEFAULT_NODE_PORT = 22