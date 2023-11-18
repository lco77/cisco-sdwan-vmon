# from doctest import ELLIPSIS_MARKER
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import click
from flask.cli import with_appcontext
from flask import current_app, g

db = SQLAlchemy()


@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    db.create_all()
    click.echo('Initialized the database.')


# TODO
# Enable command line CRUD queries for automation
@click.command('crud')
@click.option('-s', '--server', help='Server URL ex: https://vmanage.viptela.net', required=True)
@click.option('-u', '--user', help='Username', required=True)
@click.option('-p', '--password', help='Password', required=True)
@click.option('-a', '--action', help='index, read, create, edit or delete', required=True)
@click.option('-o', '--object', help='CRUD object', required=True)
@click.option('-q', '--query', help='Query parameters', required=False)
@click.option('-j', '--json', help='JSON request data', required=False)
@with_appcontext
def crud_command(server, user, password, action, object, query, json):
    """Run CRUD command."""
    api = current_app.config['api']['imported']
    if not action in ['index', 'read', 'create', 'edit', 'delete']:
        click.echo(f"Invalid action: {action}")
        return
    if not object in api.keys():
        click.echo(f"Invalid object: {action}")
        return
    click.echo(f"Not implemented, yet!")


@click.command('show-api')
@click.option('-a', '--all', is_flag=True, help='Show CRUD objects')
@click.option('-n', '--name', help='Show CRUD object details by name')
@click.option('-d', '--dual', is_flag=True, help='Show CRUD objects with 2 or more required parameters')
@click.option('-p', '--parameter', help='Show CRUD objects with specified parameter')
@with_appcontext
def show_api_command(name, all, dual, parameter):
    """Show CRUD API endpoints."""
    api = current_app.config['api']['imported']
    if name and name in api:
        click.echo(f"/api/{name}:\n{api[name]}")
    if all:
        for e in sorted(api.keys()):
            methods = [i for i in api[e]]
            click.echo(f"{e} -> {methods}")
    if dual:
        for e in sorted(api.keys()):
            for f in api[e]:
                count = 0
                params = []
                if 'path_params' in api[e][f]:
                    count = count + len(api[e][f]['path_params'])
                    [params.append(i) for i in api[e][f]['path_params']]
                if 'query_params' in api[e][f]:
                    count = count + len(api[e][f]['query_params'])
                    [params.append(i) for i in api[e][f]['query_params']]
                if count > 1:
                    click.echo(f"{e} -> {f} -> {params}")
    if parameter:
        for e in sorted(api.keys()):
            for f in api[e]:
                params = []
                if 'path_params' in api[e][f]:
                    [params.append(i) for i in api[e][f]['path_params']]
                if 'query_params' in api[e][f]:
                    [params.append(i) for i in api[e][f]['query_params']]
                if parameter in params:
                    click.echo(f"{e} -> {f} -> {params}")


# Users class
# used to store user credentials
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password = db.Column(db.String(128), unique=False, nullable=False)

    def __repr__(self):
        return '<Users %r>' % self.username

    def save(self):
        db.session.add(self)
        db.session.commit()

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def set_username(self, new_username):
        self.username = new_username


# Connections class
# used to store access data to remote APIs
class Server(db.Model):
    __tablename__ = 'connections'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    server = db.Column(db.String(64), unique=False, nullable=False)
    username = db.Column(db.String(64), unique=False, nullable=False)
    password = db.Column(db.String(128), unique=False, nullable=False)
    description = db.Column(db.String(255), unique=False, nullable=False)
    token = db.Column(db.String(255), unique=False, nullable=True)
    cookie = db.Column(db.String(255), unique=False, nullable=True)
    lock = db.Column(db.Boolean, unique=False, nullable=True)
    user = db.relationship('User', backref=db.backref("users", cascade="all, delete-orphan"))

    def __repr__(self):
        return '<Connection %r>' % self.id

    def save(self):
        db.session.add(self)
        db.session.commit()


# Load vmanage JSON API
def load_vmanageapi(data, exclude_list):
    # Init API object
    api = {}
    # HTTP methods
    http_methods = ['get', 'put', 'post', 'delete']
    # snake_case separator during name conversions
    sep = '_'
    # By separator during name conversions
    by = '_by_'  # /!\ leading _ to ensure proper alphabetical sort
    # Base vmanage URL
    basePath = data['servers'][0]['url']

    # Filter API paths
    def filter_data(data, exclude_list):
        to_delete = []
        for path in data.keys():
            for e in exclude_list:
                if path.startswith(e):
                    to_delete.append(path)
        for path in to_delete:
            del data[path]
        return data

    # Convert paths to api objects
    def data_to_objects(data, paths):
        objects = {}
        for path in paths.keys():
            object_name_substrings = []
            path_params = []
            for e in path[1:].split('/'):  # remove leading / and split by /
                # convert in_path parameter
                if e.startswith('{'):
                    e = e[1:]  # chop 1st  char
                    e = e[:-1]  # chop last char
                    path_params.append(e)
                    e = f'{by}{e}'  # prefix with 'by' separator
                else:
                    e = e.lower()
                # add substring to list
                object_name_substrings.append(e)
            # rebuild object name
            object_name = sep.join(object_name_substrings).replace('-', sep)
            # populate object 
            objects[object_name] = paths[path]
            objects[object_name]['path'] = f'{basePath}{path}'
            objects[object_name]['path_params'] = path_params
            for method in http_methods:
                if method in data['paths'][path].keys():
                    objects[object_name][method] = data['paths'][path][method]
        return objects

    # Convert object to crud function
    def object_to_crud(name, api_object, http_verb):
        crud = {}
        crud['method'] = http_verb
        crud['path'] = api_object['path']
        # copy path_params if applicable
        if '{' in crud['path']:
            crud['path_params'] = api_object['path_params']
        # extract mandatory query params if applicable
        query_params = []
        if 'parameters' in api_object[http_verb]:
            for param in api_object[http_verb]['parameters']:
                if param['in'] == 'query' and 'required' in param.keys() and param['required'] is True:
                    query_params.append(param['name'])
        if len(query_params) > 1:
            name = name.replace('__', '_')
            # print(f'INFO: {name} has multiple mandatory query params: {query_params}')
        if len(query_params) > 0:
            crud['query_params'] = query_params
        for key in ['description', 'parameters', 'requestBody']:
            if key in api_object[http_verb].keys():
                crud[key] = api_object[http_verb][key]
        return crud

    # check for required parameter function
    def is_required(parameters):
        required = False
        for p in parameters:
            if 'required' in p.keys() and p['required'] is True:
                required = True
        return required

    # Merge name-related objects into CRUD objects
    # /!\ Returns array: result + updated input data
    def merge_by_name(objects):
        # Init result object
        result = {}
        # Init list to keep track of merged objects
        merged = []
        # Init index & reverse index
        ik = {}
        ki = {}
        for i, k in enumerate(sorted(objects.keys())):
            ki[k] = i  # index_of_key
            ik[i] = k  # key_of_index
        # Loop through input objects keys
        for e in sorted(objects.keys()):
            # skip _by_someid keys
            if by in e:
                continue
            # check next key
            index = ki[e]
            f = ik[index + 1] if index + 1 in ik else None
            if f and f.startswith(e) and by in f:
                result[e] = {}
                # append e & f to merged list
                merged.append(e)
                merged.append(f)
                # Merge e
                map_crud = {'get': 'index', 'post': 'create'}
                for method in map_crud.keys():
                    if method in objects[e].keys():
                        result[e][map_crud[method]] = object_to_crud(e, objects[e], method)
                # Merge f
                map_crud = {'get': 'read', 'put': 'edit', 'delete': 'delete'}
                for method in map_crud.keys():
                    if method in objects[f].keys():
                        result[e][map_crud[method]] = object_to_crud(f, objects[f], method)
        # remove merged keys from input objects
        for e in merged:
            del objects[e]
        # remove double _ from names
        names = []
        for e in objects:
            names.append(e)
        for e in names:
            if '__' in e:
                objects[e.replace('__', '_')] = objects.pop(e)
        # return result + updated input
        return [result, objects]

    # Merge objects into CRUD objects based on http methods & required parameters
    # /!\ Returns array: result + updated input data    
    def merge_by_parameter(objects, result):
        # util function to quick-add crud action to result
        def add_crud_action(name, crud):
            if not name in result.keys():
                result[name] = {}
            if not crud in result[name].keys():
                result[name][crud] = object_to_crud(name, objects[name], verb)
                merged[name].append(verb)

        # Init list to keep track of merged path names & http verbs
        merged = {}
        for name in objects.keys():
            merged[name] = []
            for verb in http_methods:
                if verb in objects[name].keys():
                    current = objects[name][verb]
                    # some logic to infer CRUD operation from object data
                    match verb:
                        case 'get':
                            # GET with required parameter -> infer READ action
                            if 'parameters' in current.keys() and is_required(current['parameters']):
                                add_crud_action(name, 'read')
                            # GET without required parameter -> infer INDEX action
                            else:
                                add_crud_action(name, 'index')
                        case 'put':
                            # PUT with required parameter -> infer EDIT action
                            if 'parameters' in current.keys() and is_required(current['parameters']):
                                add_crud_action(name, 'edit')
                            # PUT without required parameter -> infer CREATE action
                            else:
                                add_crud_action(name, 'create')
                        case 'delete':
                            # DELETE with required parameter -> infer DELETE action
                            if 'parameters' in current.keys() and is_required(current['parameters']):
                                add_crud_action(name, 'delete')
                            # DELETE without required parameter -> infer DELETE action
                            else:
                                add_crud_action(name, 'delete')
                        case 'post':
                            # POST with required parameter -> infer EDIT action
                            if 'parameters' in current.keys() and is_required(current['parameters']):
                                add_crud_action(name, 'edit')
                            # POST without required parameter -> infer CREATE action
                            else:
                                add_crud_action(name, 'create')
        # Removed merged paths/methods from api objects
        for name in merged.keys():
            for method in merged[name]:
                del objects[name][method]
        # Remove empty objects
        to_remove = []
        for e in objects.keys():
            remove = True
            for verb in http_methods:
                if verb in objects[e].keys():
                    remove = False
            if remove is True:
                to_remove.append(e)
        for e in to_remove:
            del objects[e]
        # return result + updated input
        return [result, objects]

    # Do the job
    paths = filter_data(data['paths'], exclude_list)
    objects = data_to_objects(data, paths)
    [result, objects] = merge_by_name(objects)
    [result, objects] = merge_by_parameter(objects, result)
    return {'README': 'vMon CRUD objects imported from vManage OpenAPI data', 'imported': result, 'skipped': objects}
