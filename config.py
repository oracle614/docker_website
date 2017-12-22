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
HOME_FOLDER = os.getcwd()
