import psycopg2
from flask import current_app, g
from flask.cli import with_appcontext
from lsailor.config import Config
def init_app(app):
    app.teardown_appcontext(close_db)

def get_db():
    if 'db' not in g:
        #g.db = psycopg2.connect('dbname=lonelysailor user=sailor password=l#sailor host=lonelysailor.chghlyomwkex.us-east-2.rds.amazonaws.com port=5432')
        g.db = psycopg2.connect(dsn= Config.DATABASE_URI)
        
    return g.db

def get_db_for_scheduler():
    #db = psycopg2.connect('dbname=lonelysailor user=sailor password=l#sailor host=lonelysailor.chghlyomwkex.us-east-2.rds.amazonaws.com port=5432')
    db = psycopg2.connect(Config.DATABASE_URI)
    return db

def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()