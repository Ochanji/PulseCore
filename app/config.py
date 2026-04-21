import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'true').lower() == 'true'

    DB_ENGINE = os.environ.get('DB_ENGINE', 'sqlite')

    if DB_ENGINE == 'mysql':
        SQLALCHEMY_DATABASE_URI = os.environ.get(
            'DATABASE_URL',
            'mysql+pymysql://user:pass@localhost/pulsecore'
        )
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///pulsecore.db'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    API_VERSION = 'v1'
    WTF_CSRF_ENABLED = True
