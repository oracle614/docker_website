#!coding:utf-8

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
SECRET_KEY = 'FsdjalkfjlFfSDKFLFS'