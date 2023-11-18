import os
from flask import Flask
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from sqlalchemy.pool import NullPool
from vmanageApi import vmanageAPI
from vmonModels import init_db_command, show_api_command, crud_command, db, User, Server

# TODO: fix db connection leaks
# WORKAROUND: idle_in_transaction_session_timeout = 60000 in postgresql.conf

def create_app():
    # create and configure the app
    app = Flask('vmon', instance_relative_config=True)
    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Global settings
    app.config.from_mapping(
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        FLASK_ADMIN_SWATCH='darkly',
    )

    # Load vManage API
    exclude_list = [
        '/cloudservices', '/colocation', '/container', '/dca', '/disasterrecovery',
        '/fedramp', '/mdp', '/msla', '/multicloud', '/partner', '/sdavc', '/setting', '/sslproxy', '/statistics',
        '/stream', '/template/cor', '/tenant', '/workflow']
    app.config['api'] = vmanageAPI(os.path.join(app.root_path, 'conf', 'vmanageapi.json'), exclude_list).load()

    # Dev settings
    if os.environ['FLASK_ENV'] == 'development':
        app.config.from_mapping(
            DEBUG                   = True,
            SECRET_KEY              = 'osdbncoo84wehfcnbhezfh4wnbvzfwcnhz4owecvnzhncoa',
            SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(app.instance_path, 'db.sqlite'),
            REDIS_URL               = 'redis://127.0.0.1:6379/0',
        )

    # Prod settings
    else:
        app.config.from_mapping(
            DEBUG                   = False,
            SQLALCHEMY_ENGINE_OPTIONS = {'poolclass': NullPool,},
            #SQLALCHEMY_ENGINE_OPTIONS = {'pool': None, },
            SECRET_KEY              = os.urandom(24).hex(),
            SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL'],
            REDIS_URL               = os.environ['REDIS_URL'],
        )

    # Enable CSRF protection globally
    csrf = CSRFProtect(app)
        
    # Load SQLAlchemy with migrations
    migrate = Migrate(app, db)
    db.init_app(app)
    # engine_container = db.get_engine(app)

    # # Tear down function to close DB connections
    # @app.teardown_request
    # def teardown_request(ctx):
    #     try:
    #         #db.session.remove()
    #         db.session.close()
    #         engine_container.dispose()
    #     except:
    #         pass
    #     return None

    # Enable CSRF protection globally
    csrf = CSRFProtect(app)

    # Register 'flask init-db' command line
    app.cli.add_command(init_db_command)
    app.cli.add_command(show_api_command)
    app.cli.add_command(crud_command)

    # Enable /admin in dev mode only (no authentication required)
    if os.environ['FLASK_ENV'] == 'development':
        admin = Admin(app, name='vmon-adm', template_mode='bootstrap3')
        admin.add_view(ModelView(User, db.session))
        admin.add_view(ModelView(Server, db.session))

    # load api.py blueprint
    import vmonApi
    app.register_blueprint(vmonApi.bp)

    # load auth.py blueprint
    import vmonAuth
    app.register_blueprint(vmonAuth.bp)

    # load connections.py blueprint
    import vmanageConnections
    app.register_blueprint(vmanageConnections.bp)

    # load dashboard.py blueprint & register default view
    import vmanageDashboard
    app.register_blueprint(vmanageDashboard.bp)
    app.add_url_rule('/', endpoint='dashboard.index')

    # load devices.py blueprint
    import vmanageDevices
    app.register_blueprint(vmanageDevices.bp)

    # load policies.py blueprint
    import vmanagePolicies
    app.register_blueprint(vmanagePolicies.bp)

    # load templates.py blueprint
    import vmanageTemplates
    app.register_blueprint(vmanageTemplates.bp)

    # load alarms.py blueprint
    import vmanageAlarms
    app.register_blueprint(vmanageAlarms.bp)

    # load tasks.py blueprint
    import vmanageTasks
    app.register_blueprint(vmanageTasks.bp)

    # load lists.py blueprint
    import vmanageLists
    app.register_blueprint(vmanageLists.bp)

    # load vmonJobs.py blueprint
    import vmonJobs
    app.register_blueprint(vmonJobs.bp)

    # load doh.py blueprint
    import vmonDoh
    app.register_blueprint(vmonDoh.bp)

    return app
