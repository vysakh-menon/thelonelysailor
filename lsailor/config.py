import os

class Config(object):
    DATABASE_URI = os.environ['DATABASE_URL']