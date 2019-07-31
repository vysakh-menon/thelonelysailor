import os

from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    from . import db
    db.init_app(app)

    from . import message
    app.register_blueprint(message.bp)
    app.add_url_rule('/', endpoint='index')

    sched = BackgroundScheduler()
    sched.add_job(message.fetchFromFindMeSpot, trigger='interval', hours=1, args=[app])
    sched.start()
    atexit.register(lambda: sched.shutdown(wait=False))
    
    return app