import json
import re
from random import randint
from time import (time, sleep)
from flask import (json, current_app)
import asyncio
import httpx
from vmonModels import db, Server
from vmonJobs import (vmonQueue, rq_http_get)

# Some global variables
timeout = 15  # httpx timeout
max_retry = 2  # max httpx retry
semaphore_size = 10  # asyncio.Semaphore(n)
ssl_verify = False  # SSL cert verification
lock_sleep = 4  #


# TODO
# 'smartaccount_sync': '/dataservice/system/device/smartaccount/sync'
# {username: "xxx@domain.com", password: "xxx", validity_string: "valid"}

# class VmanageError
class VmanageError(Exception):
    ''' Basic error handling '''

    def __init__(self, message='Internal error'):
        self.message = message
        super().__init__(self.message)


# class vmanageAPI
class vmanageAPI(object):
    ''' Import & translate vMnanage API into CRUD objects '''

    def __init__(self, path, exclude_list):
        self.path = path
        self.exclude_list = exclude_list
        # some undocumented endpoints to include in CRUD API
        self.manual_endpoints = {
            'client_monitor_device_options': {
                'index': {
                    'description': 'Get realtime monitor options',
                    'method': 'get',
                    'path': '/dataservice/client/monitor/device/options',
                    'query_params': ['isCiscoDevice'],
                }
            },
            'client_activity_summary': {
                'index': {
                    'description': 'Get a summary of active tasks',
                    'method': 'get',
                    'path': '/dataservice/client/activity/summary',
                }
            }
        }

    def load(self):
        with open(self.path, encoding="utf8") as json_file:
            data = json.load(json_file)
        exclude_list = self.exclude_list
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
        # Add manual endpoints
        for k in self.manual_endpoints.keys():
            result[k] = self.manual_endpoints[k]
        return {'README': 'vMon CRUD objects imported from vManage OpenAPI data', 'imported': result,
                'skipped': objects}


# class connection
class connection(object):
    ''' Defines a connection as dict() that can be used to open a vmanage session
        Will be used in future to provide a CLI interface for scripting '''

    def __init__(self, url, username, password, description):
        for e in ['url', 'username', 'password', 'description']:
            if not type(e) is str:
                raise VmanageError(f'Init class error')
        self.server = url
        self.username = username
        self.password = password
        self.description = description

    def data(self):
        return {'server': self.server, 'username': self.username, 'password': self.password,
                'description': self.description}


# class vmanage
class vmanage(object):
    def __init__(self, id):
        ''' Init vManage session '''
        self.id = id

        # Check ID type
        def type_to_val(id):
            type_to_val = None
            if type(id) is str:
                type_to_val = 1
            if type(id) is int:
                type_to_val = 1
            if type(id) is dict:
                type_to_val = 2
            return type_to_val

        # Set connection data from Dict or DB
        match type_to_val(id):
            # int or str -> get from DB
            case 1:
                self.id_source = 'db'
                # Get connection data from db
                c = db.session.query(Server).filter_by(id=id).first()
                if c.server and c.username and c.password and c.description:
                    self.host = c.server
                    self.username = c.username
                    self.password = c.password
                    self.description = c.description
                    # Get tokens from DB
                    if c.token and c.cookie:
                        self.cookies = {'JSESSIONID': c.cookie}
                        self.headers = {'Accept': 'application/json', 'Content-Type': 'application/json',
                                        'Connection': 'keep-alive', 'X-XSRF-TOKEN': c.token}
                    # Get tokens from vManage
                    else:
                        try:
                            self.lock_or_wait(c)
                        except VmanageError as error:
                            raise VmanageError(str(error))
                else:
                    raise VmanageError(f'Init Error getting connection {self.id} info')
            # dict -> get from Dict
            case 2:
                self.id_source = 'dict'
                # Get connection data from connection class
                self.host = id['server']
                self.username = id['username']
                self.password = id['password']
                self.description = id['description']
                # Get tokens from vManage
                self.cookies = {'JSESSIONID': self.make_auth_token()}
                self.headers = {'Accept': 'application/json', 'Content-Type': 'application/json',
                                'Connection': 'keep-alive', 'X-XSRF-TOKEN': self.make_csrf_token()}
            case _:
                raise VmanageError(f'Init class error')

    def lock_or_wait(self, c):
        # Refresh data after short random wait
        delay = randint(1, 10) / 10
        sleep(delay)
        db.session.refresh(c)
        # Another instance has lock : wait and get new tokens from DB
        if c.lock and c.lock is True:
            print(f'LOCK WAIT ({delay}s) on {self.host}: waiting for new tokens')
            sleep(lock_sleep)
            # Read new tokens
            db.session.refresh(c)
            self.auth_token = c.cookie
            self.csrf_token = c.token
        # Acquire lock and get fresh tokens
        else:
            c.lock = True
            db.session.commit()
            print(f'LOCK ACQUIRED ({delay}s) on {self.host}: fetching new tokens')
            self.close()
            try:
                self.auth_token = self.make_auth_token()
                self.csrf_token = self.make_csrf_token()
            except:
                # c = db.session.query(Server).filter_by(id=self.id).first()
                c.lock = False
                db.session.commit()
                raise VmanageError(f'Failed to refresh tokens from {self.host}')
            # Save new tokens
            # c = db.session.query(Server).filter_by(id=self.id).first()
            c.token = self.csrf_token
            c.cookie = self.auth_token
            c.lock = False
            db.session.commit()
        # Finally set session
        self.cookies = {'JSESSIONID': self.auth_token}
        self.headers = {'Accept': 'application/json', 'Content-Type': 'application/json', 'Connection': 'keep-alive',
                        'X-XSRF-TOKEN': self.csrf_token}

    def make_auth_token(self):
        """ POST request to fetch JSESSIONID """
        r = None
        try:
            with httpx.Client(timeout=timeout, verify=ssl_verify) as client:
                r = client.post(f'{self.host}/dataservice/j_security_check',
                                data={'j_username': self.username, 'j_password': self.password})
        except httpx.RequestError as error:
            raise VmanageError(f'Authenticating {self.username} to {self.host} failed: {str(error)}')
        if r.status_code != 200 or r.text.startswith('<html>'):
            raise VmanageError(f'Authenticating {self.username} to {self.host} failed: {r.status_code}')
        else:
            self.auth_token = r.cookies['JSESSIONID']
            return self.auth_token

    def make_csrf_token(self):
        """ GET request to fetch X-XSRF-TOKEN """
        r = None
        try:
            with httpx.Client(timeout=timeout, verify=ssl_verify, cookies={'JSESSIONID': self.auth_token}) as client:
                r = client.get(f'{self.host}/dataservice/client/token')
        except httpx.RequestError as error:
            raise VmanageError(f'Authenticating {self.username} to {self.host} failed: {str(error)}')
        if r.status_code != 200 or r.text.startswith('<html>'):
            raise VmanageError(f'Authenticating {self.username} to {self.host} failed: {r.status_code}')
        else:
            self.csrf_token = r.text
            return self.csrf_token

    def make_tokens(self):
        """ POST request to fetch JSESSIONID """
        r = None
        try:
            with httpx.Client(timeout=timeout, verify=ssl_verify) as client:
                r = client.post(f'{self.host}/dataservice/j_security_check',
                                data={'j_username': self.username, 'j_password': self.password})
                if r.status_code != 200 or r.text.startswith('<html>'):
                    raise VmanageError(f'Authenticating {self.username} to {self.host} failed: {r.status_code}')
                auth_token = r.cookies['JSESSIONID']
                r = client.get(f'{self.host}/dataservice/client/token')
                if r.status_code != 200 or r.text.startswith('<html>'):
                    raise VmanageError(f'Authenticating {self.username} to {self.host} failed: {r.status_code}')
                csrf_token = r.text
        except httpx.RequestError as error:
            raise VmanageError(f'Authenticating {self.username} to {self.host} failed: {str(error)}')
        self.auth_token = auth_token
        self.csrf_token = csrf_token
        return (self.auth_token, self.csrf_token)

    def close(self):
        ''' Offload Logout to RQ scheduler '''
        url = f'{self.host}/logout'
        try:
            q = vmonQueue('vmonJobs')
            q.add_job(rq_http_get, url=url, timeout=timeout, verify=ssl_verify, headers=self.headers,
                      cookies=self.cookies, params={'nocache': str(int(time()))})
            # rq_queue('vmonJobs',rq_http_get, url=url, timeout=timeout, verify=ssl_verify, headers=self.headers, cookies=self.cookies, params={'nocache': str(int(time()))} )
        except:
            pass
        return None

    async def crud(self, action, object, args, payload):
        ''' CRUD API derived from vManage OpenAPI data
            see /api for the list of supported objects and actions
            see vmon.js for crud() client '''
        before = time()
        # get API definition
        try:
            api = current_app.config['api']['imported'][object][action]
        except:
            raise VmanageError(f'Invalid request: {action}({object})')
        # Process args if any
        path = api['path']
        query = ''
        if not args is None:
            # map mandatory path_params
            args_list = [arg for arg in args]
            if 'path_params' in api:
                for p in api['path_params']:
                    if p in args_list:
                        path = path.replace(f"{{{p}}}", args[p])
                        args.pop(p)
                    else:
                        raise VmanageError(f'Parameter {p} is missing')
            # map mandatory query_params
            args_list = [arg for arg in args]
            if 'query_params' in api:
                query = '?'
                for p in api['query_params']:
                    if p in args_list:
                        query = f"{query}{p}={args[p]}&"
                        args.pop(p)
                    else:
                        raise VmanageError(f'Parameter {p} is missing')
                # chop trailing &
                query = query[:-1]
            # map remaining optional query params
            args_list = [arg for arg in args]
            for p in args_list:
                if query == '':
                    query = f"?{p}={args[p]}"
                else:
                    query = f"{query}&{p}={args[p]}"
        # payload
        if isinstance(payload, dict):
            payload = json.dumps(payload)
        else:
            payload = None
            # build request URL
        url = f"{self.host}{path}{query}"

        # Fetch helper function to query vManage
        async def fetch(retry, msg):
            if retry == max_retry:
                raise VmanageError(f'{msg}:Too many retries ({retry})')
            # send request with appropriate method
            r = None
            try:
                async with httpx.AsyncClient(timeout=timeout, headers=self.headers, cookies=self.cookies,
                                             verify=ssl_verify) as client:
                    match api['method']:
                        case 'get':
                            r = await client.get(url)
                        case 'delete':
                            r = await client.delete(url)
                        case 'post':
                            r = await client.post(url, data=payload)
                        case 'put':
                            r = await client.put(url, data=payload)
                # Enable for useful debug info
                # print(f"CRUD-API: request-headers: {r.request.headers}")
                # print(f"CRUD-API: {r.status_code} - {api['method']} - {url}", flush=True)
                # print(f"CRUD-API: response-headers: {r.headers}")
                r.raise_for_status()
            except httpx.TimeoutException as exc:
                return await fetch(retry + 1, f'{msg}:httpx.TimeoutException;Retry {retry + 1}:')
            except httpx.RequestError as exc:
                return await fetch(retry + 1, f'{msg}:httpx.RequestError;Retry {retry + 1}:')
            except httpx.HTTPStatusError as exc:
                return await fetch(retry + 1,
                                   f'{msg}:httpx.HTTPStatusError {exc.response.status_code};Retry {retry + 1}:')
            # Check if we need to refresh tokens
            if 'must-revalidate' in r.headers.get('cache-control') and r.text.startswith('<html>'):
                print(f'CRUD-API: new tokens required for {self.host}')
                # Update tokens in DB if applicable
                if self.id_source == 'db':
                    c = db.session.query(Server).filter_by(id=self.id).first()
                    try:
                        self.lock_or_wait(c)
                    except VmanageError as error:
                        raise VmanageError(str(error))
                else:
                    # Schedule old tokens for removal
                    self.close()
                    try:
                        self.auth_token = self.make_auth_token()
                        self.csrf_token = self.make_csrf_token()
                    except:
                        raise VmanageError(f'Error fetching session tokens - try again')
                # Finaly update session
                self.cookies = {'JSESSIONID': self.auth_token}
                self.headers = {'Accept': 'application/json', 'Content-Type': 'application/json',
                                'Connection': 'keep-alive', 'X-XSRF-TOKEN': self.csrf_token}
                # Recurse until max_retry
                return await fetch(retry + 1, f'{msg}:Tokens renewed;Retry {retry + 1}:')
            else:
                return r

        # Fetch data
        try:
            r = await fetch(0, f'Retry 0:')
            r = r.json()
        except VmanageError as error:
            raise VmanageError(f"CRUD-API error: {api['method']} - {url} : {error}")
        after = time()
        delta = after - before
        print(f"CRUD-API: {delta}s - {api['method']} - {url}", flush=True)
        return r

    async def cruds(self, objects):
        ''' Helper for concurrent crud() requests
            objects = [{'action':action, 'object':object, 'args':args, 'payload':payload}, ...]
            see vmon.js for cruds() client '''
        semaphore = asyncio.Semaphore(semaphore_size)

        async def sem_task(task):
            async with semaphore:
                return await task

        tasks = [self.crud(e['action'], e['object'], e['args'], e['payload']) for e in objects]
        return await asyncio.gather(*(sem_task(task) for task in tasks), return_exceptions=True)


# Class vedge
class vedge(object):
    def __init__(self, session, systemip):
        self.id = systemip
        self.session = session
        self.cache = {}

    async def data(self):
        ''' Fetch and cache basic device data '''
        # cache lookup
        if 'data' in self.cache.keys():
            return self.cache['data']
        # get data
        try:
            s = self.session
            r = await s.crud('index', 'device', {'system-ip': self.id}, None)
        except:
            raise VmanageError(f'get data failed')
        self.cache['data'] = r['data'][0]
        return self.cache['data']

    async def details(self):
        ''' Fetch and cache detailed device data '''
        # cache lookup
        if 'details' in self.cache.keys():
            return self.cache['details']
        # get data
        try:
            s = self.session
            r = await s.crud('read', 'system_device', {'deviceCategory': 'vedges', 'deviceIP': self.id}, None)
            self.cache['details'] = r['data'][0]
        except:
            raise VmanageError(f'get device details failed')
        return self.cache['details']

    async def bfdsessions(self):
        ''' Fetch and cache BFD sessions '''
        if 'bfdsessions' in self.cache.keys():
            return self.cache['bfdsessions']
        # Get actual data
        try:
            s = self.session
            r = await s.crud('read', 'device_bfd_synced_sessions', {'deviceId': self.id}, None)
        except:
            return None
        # Compute session list
        list = []
        for e in r['data']:
            list.append({
                'source': e['vmanage-system-ip'],
                'target': e['system-ip'],
                'state': e['state'],
                'local-color': e['local-color'],
                'remote-color': e['color'],
            })
            # Fill cache
        self.cache['bfdsessions'] = list
        # Return cache
        return self.cache['bfdsessions']

    async def tlocs(self):
        ''' Fetch and cache TLOCS '''
        # Look up cache
        if 'tlocs' in self.cache.keys():
            return self.cache['tlocs']
        # Get actual data
        try:
            s = self.session
            r = await s.crud('read', 'device_control_synced_waninterface', {'deviceId': self.id}, None)
        except:
            return None
        # Compute tloc list
        list = []
        for e in r['data']:
            list.append({
                'color': e['color'],
                'state': e['operation-state'],
                'preference': e['preference'],
                'restrict': e['restrict-str'],
            })
        # Fill cache
        self.cache['tlocs'] = list
        # Return cache
        return self.cache['tlocs']

    async def getConfig(self, type):
        ''' Fetch sdwan or running config from device '''
        # Process input
        if type == 'running':
            object = 'template_config_running_by_deviceId'
        elif type == 'sdwan':
            object = 'template_config_attached_by_deviceId'
        else:
            return None
        # Replace / in ENCS chassis ID
        id = self.id.replace('/', '%2F')
        # Query vManage
        try:
            s = self.session
            r = await s.crud('read', object, {'deviceId': id}, None)
        except:
            return None
        # Return data
        return r


# class deviceTemplate
class deviceTemplate(object):
    def __init__(self, session, id):
        self.id = id
        self.session = session
        self.cache = {}

    async def data(self):
        ''' Fetch and cache device template data '''
        # cache lookup
        if 'data' in self.cache.keys():
            return self.cache['data']
        # get data
        try:
            s = self.session
            r = await s.crud('read', 'template_device_object_by_templateId', {'templateId': self.id}, None)
            self.cache['data'] = r
        except:
            raise VmanageError(f'instanciation of template {id} failed')
        return self.cache['data']

    async def feature_templates(self):
        ''' Fetch and cache feature template data '''
        # cache lookup
        if 'feature_templates' in self.cache.keys():
            return self.cache['feature_templates']
        # get data
        try:
            s = self.session
            r = await s.crud('index', 'template_feature', {'summary': True}, None)
            self.cache['feature_templates'] = r
        except:
            raise VmanageError(f'get_feature_templates failed')
        return self.cache['feature_templates']

    async def attachments(self):
        ''' Fetch and cache template device attachements '''
        # cache lookup
        if 'attachments' in self.cache.keys():
            return self.cache['attachments']
        # get data
        try:
            s = self.session
            r = await s.crud('read', 'template_device_config_attached_by_masterTemplateId',
                             {'masterTemplateId': self.id}, None)
            self.cache['attachments'] = r
        except:
            raise VmanageError(f'get_attachments failed')
        return self.cache['attachments']

    async def values(self, uuid=None):
        ''' Fetch and cache device template variables and values '''
        # cache lookup
        if f'device_values_{uuid}' in self.cache.keys():
            return self.cache[f'device_values_{uuid}']
        # uuid=None to get template variables only
        if uuid is None:
            deviceIds = []
        # uuid=0 to get variables and values of all attached devices
        elif uuid == '0':
            # get attached devices
            try:
                r = await self.attachments()
                deviceIds = [e['uuid'] for e in r['data']]
            except VmanageError as error:
                raise VmanageError(f'get_values failed: {error}')
        # uuid=deviceid to get variables and values of one device
        else:
            deviceIds = [uuid]
        # create request payload
        payload = {"deviceIds": deviceIds, "isEdited": False, "isMasterEdited": False, "templateId": self.id}
        # get data
        try:
            s = self.session
            r = await s.crud('create', 'template_device_config_input', None, payload)
        except:
            raise VmanageError(f'get_values failed')
        # Process header data
        header = []
        regex_variable = re.compile(r'\((?P<variable>[^(]+)\)')
        regex_name = re.compile(r'^(?P<name>[\w\s/-]+)\(')
        # Loop on headers
        for h in r['header']['columns']:
            # if h['property'] == 'csv-status':
            #    continue

            entry = {}
            # data type
            entry['dataType'] = h['dataType']
            # property name
            entry['property'] = h['property']
            # Extract title
            match = regex_name.search(h['title'])
            if match:
                entry['title'] = match.groups('name')[0]
            else:
                entry['title'] = h['title']
            # Extract variable name
            match = regex_variable.search(h['title'])
            if match:
                entry['variable'] = match.groups('variable')[0]
            else:
                entry['variable'] = h['property']
            # editable
            entry['editable'] = h['editable']
            # optional
            if 'optional' in h.keys():
                entry['optional'] = h['optional']
            else:
                entry['optional'] = False
            # values
            if 'values' in h.keys():
                entry['values'] = h['values']
            else:
                entry['values'] = False
            # init a breadcrumb to facilitate input grouping on client side
            breadcrumb = ''
            # Extract level 1 breadcrumb
            property_path = h['property'].split('/')
            if len(property_path) == 1:
                entry['category'] = 'Hidden'
            elif re.match('\d', property_path[1]):
                entry['category'] = f'Vpn-{property_path[1]}'
                breadcrumb = entry['category']
            else:
                entry['category'] = 'System'
                breadcrumb = entry['category']
            # Extract level 2 breadcrumb
            if 'templateType' in h.keys():
                entry['templateType'] = h['templateType']
            else:
                entry['templateType'] = ''
            if not entry['templateType'] in ['', 'None', 'cisco_system', 'cisco_logging', 'cisco_snmp']:
                breadcrumb = f"{breadcrumb} > {entry['templateType']}"
            # Extract level 3 breadcrumb
            prop = h['property']
            list = prop.split('/')
            if entry['templateType'] == 'cisco_vpn_interface':
                breadcrumb = f"{breadcrumb} > {list[2]}"
            elif entry['templateType'] == 'vpn-interface-svi':
                breadcrumb = f"{breadcrumb} > {list[2]}"
            elif entry['templateType'] == 'switchport':
                breadcrumb = f"{breadcrumb} > {list[4]}"
            elif len(list) >= 6 and list[5] == 'neighbor':
                breadcrumb = f"{breadcrumb} > {list[6]}"
            entry['breadcrumb'] = breadcrumb
            # Fix empty breadcrumb for CSV values
            if breadcrumb == '':
                entry['breadcrumb'] = 'CSV'
            # Add entry to header list
            header.append(entry)
        # Add headers and data to cache & reply
        self.cache[f'device_values_{uuid}'] = {'header': header, 'data': r['data']}
        return self.cache[f'device_values_{uuid}']

    async def csv(self, uuid):
        ''' Fetch and cache device template values in CSV format '''
        # cache lookup
        if 'csv' in self.cache.keys():
            return self.cache['csv']
        # Get values
        try:
            data = await self.values(uuid)
        except:
            raise VmanageError(f'csv_file failed')
        # Make CSV header without csv-status property to replicate vManage behavior
        header_list = [e["property"] for e in data['header'] if e["property"] != 'csv-status']
        csv = ','.join([f'"{e}"' for e in header_list])
        if not uuid is None:
            # Make CSV row without csv-status property to replicate vManage behavior
            value_list = [data["data"][0][key].replace('TEMPLATE_IGNORE', '') for key in header_list if
                          key != 'csv-status']
            value_csv = ','.join([f'"{e}"' for e in value_list])
            csv = csv + '\n' + value_csv
        self.cache['csv'] = csv
        return self.cache['csv']

    async def attach(self, payload):
        ''' Attach device template to one or more devices '''
        try:
            s = self.session
            r = s.crud('create', 'template_device_config_attachfeature', None, payload)
        except:
            raise VmanageError(f'device template attachment failed')
        return r

    async def hierarchy(self):
        ''' Create a hierarchical template data structure compatible with d3.js '''
        # cache lookup
        if 'hierarchy' in self.cache.keys():
            return self.cache['hierarchy']
        # gather some data
        try:
            tasks = [self.data(), self.feature_templates()]
            (device_template, feature_templates) = await asyncio.gather(*tasks, return_exceptions=True)
        except:
            raise VmanageError(f'get_hierarchy failed')

        # make_tree
        # - parse 'data' recursively following 'childmap' items and save 'attrmap' attributes
        # - rename attributes using 'attrmap' values
        def make_tree(data: list, childmap: list, attrmap: dict):
            result = {}
            for e in data:
                for k in e.keys():
                    # map attributes
                    if k in attrmap.keys():
                        result[attrmap[k]] = e[k]
                    # recurse for children
                    if k in childmap:
                        result['children'] = [make_tree([f], childmap, attrmap) for f in e[k]]
            return result

        # map_attributes in 'data' objects with elements from 'source' list, joining on 'match' map
        # - parse 'data' recursively
        # - match 'source' elements with 'data' elements using 'matchmap'
        # - map 'source' attributes with 'data' attributes using 'attrmap'
        def map_attributes(data: list, matchmap: dict, attrmap: dict, source: list):
            result = {}
            # loop through data objects
            for d in data:
                # Copy original keys
                for k in d.keys():
                    if k != 'children':
                        result[k] = d[k]
                # check if we have a match element
                s_key = list(matchmap.keys())[0]
                d_key = matchmap[s_key]
                # is there a key to match with ?
                if d_key in d.keys():
                    # loop through source list
                    for s in source:
                        # find match in source list
                        if s[s_key] and s[s_key] == d[d_key]:
                            # now check for attributes to map
                            for a in attrmap.keys():
                                s_attr = a
                                d_attr = attrmap[a]
                                # map attribute
                                if s[s_attr]:
                                    result[d_attr] = s[s_attr]
                # recurse if object has children
                if 'children' in d.keys():
                    result['children'] = [map_attributes([child], matchmap, attrmap, source) for child in d['children']]
            return result

        # Make tree
        childmap = ['generalTemplates', 'subTemplates']
        attrmap = {'templateId': 'id', 'templateType': 'type', 'templateName': 'name',
                   'templateDescription': 'description'}
        tree = make_tree([device_template], childmap, attrmap)
        # Map attributes
        matchmap = {'templateId': 'id'}
        attrmap = {'templateName': 'name', 'templateDescription': 'description'}
        self.cache['hierarchy'] = map_attributes([tree], matchmap, attrmap, feature_templates['data'])
        return self.cache['hierarchy']


# Class policy
class vmanagePolicy(object):
    def __init__(self, session, flavor, id):
        self.id = id
        self.flavor = flavor
        self.session = session
        self.cache = {}
        self.policyTypes = {
            'vsmart': 'template_policy_vsmart_definition_by_policyId',
            'vedge': 'template_policy_vedge_definition_by_policyId',
            'security': 'template_policy_security_definition_by_policyId',
        }
        self.policyDefinitionTypes = {
            'control': 'template_policy_definition_control',
            'appRoute': 'template_policy_definition_approute',
            'vedgeRoute': 'template_policy_definition_vedgeroute',
            'data': 'template_policy_definition_data',
            'cflowd': 'template_policy_definition_cflowd',
            'zoneBasedFW': 'template_policy_definition_zonebasedfw',
            'qosMap': 'template_policy_definition_qosmap',
            'acl': 'template_policy_definition_acl',
        }
        self.policyListTypes = {
            'sourceZone': 'template_policy_list_zone',
            'destinationZone': 'template_policy_list_zone',
            'sourceDataPrefixList': 'template_policy_list_dataprefix',
            'destinationDataPrefixList': 'template_policy_list_dataprefix',
            'destinationFqdnList': 'template_policy_list_fqdn',
            'destinationPortList': 'template_policy_list_port',
            'colorList': 'template_policy_list_color',
            'prefixList': 'template_policy_list_prefix',
            'tlocList': 'template_policy_list_tloc',
            'siteList': 'template_policy_list_site',
            'vpnList': 'template_policy_list_vpn',
            'name': 'template_policy_list_sla',
            'address': 'template_policy_list_ipprefixall',
            'classMap': 'template_policy_list_class',
        }

    async def policyList(self, id, type):
        ''' Fetch and cache list data '''
        # cache lookup
        if f'list-{type}-{id}' in self.cache.keys():
            return self.cache[f'list-{type}-{id}']
        # get data
        try:
            s = self.session
            r = await s.crud('index', self.policyListTypes[type], None, None)
        except VmanageError as error:
            raise VmanageError(f'get {type} list {id} failed: {error}')
        # Populate cache
        for e in r['data']:
            self.cache[f'list-{type}-{e["listId"]}'] = e
        return self.cache[f'list-{type}-{id}']

    async def policyData(self):
        ''' Fetch and cache policy data '''
        # cache lookup
        if 'data' in self.cache.keys():
            return self.cache['data']
        # get data
        try:
            s = self.session
            r = await s.crud('read', self.policyTypes[self.flavor], {'policyId': self.id}, None)
            self.cache['data'] = r
        except VmanageError as error:
            raise VmanageError(f'get {self.flavor} policy {self.id} failed: {error}')
        return self.cache['data']

    async def policyDefinition(self, id, type):
        ''' Fetch and cache policy definition data '''
        # cache lookup
        if f'definition-{type}-{id}' in self.cache.keys():
            return self.cache[f'definition-{type}-{id}']
        # get data
        try:
            s = self.session
            r = await s.crud('read', self.policyDefinitionTypes[type], {'id': id}, None)
            self.cache[f'definition-{type}-{id}'] = r
        except VmanageError as error:
            raise VmanageError(f'get {type} definition {id} failed: {error}')
        return self.cache[f'definition-{type}-{id}']

    async def tree(self, id, flavor):
        ''' Create a hierarchical policy data structure compatible with d3.js'''

        # Parse list
        async def parse_list(type, id):
            # Special case with id = self
            if id == 'self':
                return {
                    'vmanage-id': 'self',
                    'name': 'self',
                    'description': 'self',
                    'object': 'list',
                    'type': type,
                    'color': '#adb5bd',
                    'stroke': '#ebebeb',
                    'size': 7,
                }
            # Get data
            try:
                list = await self.policyList(id, type)
            except VmanageError as error:
                return {"error": str(error)}
            # parse list
            parsed = ''
            for e in list['entries']:
                parsed = f"{parsed}["
                for k in e.keys():
                    parsed = f"{parsed}{k}={e[k]} "
                parsed = parsed[:-1]
                parsed = f"{parsed}]\n"
            parsed = parsed[:-1]
            # prepare result
            result = {
                'vmanage-id': list['listId'],
                'name': list['name'],
                'description': parsed,
                'object': 'list',
                'type': list['type'],
                'color': '#adb5bd',
                'stroke': '#ebebeb',
                'size': 7,
            }
            # stick to type from request
            if type != 'name':
                result['type'] = type
            return result

        # Parse policy
        def parse_policy(policy, id, flavor):
            #print(policy)
            desc = None
            match flavor:
                case 'security':
                    settings = None
                    if 'settings' in policy['policyDefinition'].keys():
                        list = [f"{e}: {policy['policyDefinition']['settings'][e]}" for e in
                                policy['policyDefinition']['settings']]
                        settings = '\n'.join(list)
                    desc = f"{policy['policyDescription']}\nUse case: {policy['policyUseCase']}\n{settings}"
                case _:
                    desc = policy['policyDescription']
            return {
                'id': id,
                'vmanage-id': id,
                'name': policy['policyName'],
                'description': desc,
                'object': 'policy',
                'type': flavor,
                'assembly': policy['policyDefinition']['assembly'],
                'children': [],
                'parent': None,
                'color': 'white',
                'stroke': '#ebebeb',
                'size': 10,
            }

        # Parse definition
        def parse_definition(definition, parentId):
            #print(definition)
            desc = None
            color = None
            match definition['type']:
                case 'control':
                    desc = definition['description']
                    color = "#00bc8c"
                case 'appRoute':
                    desc = definition['description']
                    color = "#f39c12"
                case 'data':
                    desc = definition['description']
                    color = "#e74c3c"
                case 'cflowd':
                    props = definition['definition']['customizedIpv4RecordFields']
                    desc = '\n'.join([f'{propName}: {props[propName]}' for propName in props.keys()])
                    color = "#3498db"
                case 'zoneBasedFW':
                    desc = definition['description']
                    color = "#e74c3c"
                case 'qosMap':
                    desc = definition['description']
                    color = "#adb5bd"
                case 'acl':
                    desc = definition['description']
                    color = "#adb5bd"
                case _:
                    desc = definition['description']
                    color = "#adb5bd"
            newDefinition = {
                'id': f"{parentId}-{definition['definitionId']}",
                'vmanage-id': definition['definitionId'],
                'type': definition['type'],
                'object': 'definition',
                'name': definition['name'],
                'description': desc,
                'children': [],
                'parent': parentId,
                'color': color,
                'stroke': '#ebebeb',
                'size': 9,
            }
            # Handle special cases (zoneBasedFW)
            if 'definition' in definition.keys():
                for key in ['entries', 'sequences', 'defaultAction']:
                    if key in definition['definition'].keys():
                        # print(f"copy key {key} with val {definition['definition'][key]}")
                        definition[key] = definition['definition'][key]
            # if 'definition' in definition.keys() and 'entries' in definition['definition'].keys():
            #    definition['entries'] = definition['definition']['entries']
            # if 'definition' in definition.keys() and 'sequences' in definition['definition'].keys():
            #    definition['sequences'] = definition['definition']['sequences']
            return newDefinition

        # Parse qosSchedulers
        async def parse_schedulers(schedulers, parentId):
            newSchedulers = []
            index = 0
            for scheduler in schedulers:
                index += 1
                id = f"{parentId}-scheduler-{index}"
                className = "control"
                if scheduler['classMapRef'] != '':
                    classData = await parse_list('classMap', scheduler['classMapRef'])
                    className = classData['name']

                classInfo = {
                    'id': f"{id}-classData",
                    'vmanage-id': None,
                    'object': '',
                    'name': className,
                    'description': "",
                    'type': 'Class',
                    'parent': id,
                    'color': "#adb5bd",  # grey
                    'stroke': '#ebebeb',
                    'size': 8,
                    'children': None
                }

                bandwidthPercent = {
                    'id': f"{id}-bandwidthPercent",
                    'vmanage-id': None,
                    'object': '',
                    'name': f'{scheduler["bandwidthPercent"]} Percent',
                    'description': "",
                    'type': 'Bandwith',
                    'parent': id,
                    'color': "#adb5bd",  # grey
                    'stroke': '#ebebeb',
                    'size': 8,
                    'children': None
                }

                bufferPercent = {
                    'id': f"{id}-bufferPercent",
                    'vmanage-id': None,
                    'object': '',
                    'name': f'{scheduler["bufferPercent"]} Percent',
                    'description': "",
                    'type': 'Buffer',
                    'parent': id,
                    'color': "#adb5bd",  # grey
                    'stroke': '#ebebeb',
                    'size': 8,
                    'children': None
                }

                scheduling = {
                    'id': f"{id}-scheduling",
                    'vmanage-id': None,
                    'object': '',
                    'name': f'{scheduler["scheduling"]}',
                    'description': "",
                    'type': 'Scheduling policy',
                    'parent': id,
                    'color': "#adb5bd",  # grey
                    'stroke': '#ebebeb',
                    'size': 8,
                    'children': None
                }

                drops = {
                    'id': f"{id}-drops",
                    'vmanage-id': None,
                    'object': '',
                    'name': f'{scheduler["drops"]}',
                    'description': "",
                    'type': 'Drop policy',
                    'parent': id,
                    'color': "#adb5bd",  # grey
                    'stroke': '#ebebeb',
                    'size': 8,
                    'children': None
                }

                newScheduler = {
                    'id': id,
                    'vmanage-id': None,
                    'object': '',
                    'name': f"",
                    'description': f"",
                    'type': f"queue {scheduler['queue']}",
                    'parent': parentId,
                    'color': '#3498db',  # blue
                    'stroke': '#ebebeb',
                    'size': 8,
                    'children': [classInfo, bandwidthPercent, bufferPercent, scheduling, drops],
                }
                newSchedulers.append(newScheduler)
            return newSchedulers

        # Parse collectors
        def parse_collectors(collectors, parentId):
            newCollectors = []
            index = 0
            for collector in collectors:
                index += 1
                id = f"{parentId}-collector-{index}"
                transport = {
                    'id': f"{id}-transport",
                    'vmanage-id': None,
                    'object': 'protocol',
                    'name': collector['transport'],
                    'description': collector['transport'],
                    'type': 'set',
                    'parent': id,
                    'color': '#3498db',  # blue
                    'stroke': '#ebebeb',
                    'size': 8,
                    'children': None
                }
                vpn = {
                    'id': f"{id}-vpn",
                    'vmanage-id': None,
                    'object': 'vpn',
                    'name': collector['vpn'],
                    'description': collector['vpn'],
                    'type': 'set',
                    'parent': id,
                    'color': '#3498db',  # blue
                    'stroke': '#ebebeb',
                    'size': 8,
                    'children': None
                }
                sourceInterface = {
                    'id': f"{id}-sourceInterface",
                    'vmanage-id': None,
                    'object': 'sourceInterface',
                    'name': collector['sourceInterface'],
                    'description': collector['sourceInterface'],
                    'type': 'set',
                    'parent': id,
                    'color': '#3498db',  # blue
                    'stroke': '#ebebeb',
                    'size': 8,
                    'children': None
                }
                address = {
                    'id': f"{id}-address",
                    'vmanage-id': None,
                    'object': 'address',
                    'name': collector['address'],
                    'description': collector['address'],
                    'type': 'set',
                    'parent': id,
                    'color': '#3498db',  # blue
                    'stroke': '#ebebeb',
                    'size': 8,
                    'children': None
                }
                port = {
                    'id': f"{id}-port",
                    'vmanage-id': None,
                    'object': 'port',
                    'name': collector['port'],
                    'description': collector['port'],
                    'type': 'set',
                    'parent': id,
                    'color': '#3498db',  # blue
                    'stroke': '#ebebeb',
                    'size': 8,
                    'children': None
                }
                newCollector = {
                    'id': id,
                    'vmanage-id': None,
                    'object': 'sequence',
                    'name': f"Collector {index}",
                    'description': f"Collector {index}",
                    'type': 'cflowd',
                    'parent': parentId,
                    'color': '#3498db',  # blue
                    'stroke': '#ebebeb',
                    'size': 8,
                    'children': [vpn, sourceInterface, transport, address, port]
                }
                newCollectors.append(newCollector)
            return newCollectors

        # Parse sequence
        def parse_sequence(sequence, parentId):
            color = None
            match sequence['sequenceType']:
                case 'tloc':
                    color = "#f39c12"  # orange
                case 'route':
                    color = "#00bc8c"  # green
                case 'zoneBasedFW':
                    color = "#adb5bd"  # grey
                case _:
                    color = "#adb5bd"  # grey
            newSequence = {
                'id': f"{parentId}-{sequence['sequenceId']}",
                'vmanage-id': sequence['sequenceId'],
                'object': 'sequence',
                'name': sequence['sequenceName'],
                'description': f"index: {sequence['sequenceId']}\ntype: {sequence['sequenceType']}\nname: {sequence['sequenceName']}",
                'type': sequence['sequenceType'],
                'children': [],
                'parent': parentId,
                'color': color,
                'stroke': '#ebebeb',
                'size': 8,
            }
            return newSequence

        # Parse entries (direction + lists)
        async def parse_entries(entries, parentId):
            newEntries = []
            for entry in entries:
                newEntry = dict()
                for key in entry.keys():
                    if key == 'direction':
                        newEntry['direction'] = entry[key]
                    else:
                        lists = []
                        # convert string to array (zone lists only)
                        if type(entry[key]) is str:
                            entry[key] = [entry[key]]
                        for ref in entry[key]:
                            # chop last character from key (shown in plural form by vmanage) except for some keys..
                            if key in ['sourceZone', 'destinationZone']:
                                key += 'x'
                            list = await parse_list(key[:-1], ref)
                            # Add some context data to object
                            list['id'] = f"{parentId}-{list['vmanage-id']}"
                            list['object'] = 'scope'
                            list['children'] = None
                            list['parent'] = parentId
                            lists.append(list)
                        # Add lists to definition
                        newEntry['lists'] = list
                newEntries.append(newEntry)
            return newEntries

        # Parse match conditions
        async def parse_match(entries, parentId):
            newEntries = []
            for match in entries:
                newMatch = dict()
                # Resolve reference to list
                if 'ref' in match.keys():
                    newMatch = await parse_list(match["field"], match["ref"])
                    newMatch['id'] = f"{parentId}-{newMatch['vmanage-id']}"
                    newMatch['object'] = 'match'
                    newMatch['parent'] = parentId
                    newMatch['children'] = None
                # No reference: build-up object
                else:
                    newMatch = {
                        'id': f"{parentId}-match-{match['field']}-{match['value']}",
                        'vmanage-id': 'None',
                        'object': 'match',
                        'type': match['field'],
                        'name': match['value'],
                        'description': f"{match['field']}: {match['value']}",
                        'parent': parentId,
                        'children': None,
                        'color': '#adb5bd',
                        'stroke': '#ebebeb',
                        'size': 8,
                    }
                # return parsed value
                newEntries.append(newMatch)
            return newEntries

        # Parse actions
        async def parse_action(actions, parentId):
            newActions = []
            for action in actions:
                newAction = dict()
                if 'parameter' in action.keys():
                    # Convert param string into array object, if needed
                    if type(action['parameter']) is str:
                        action['parameter'] = [{'value': action['parameter']}]
                    # Loop on parameter object
                    for param in action['parameter']:
                        # Resolve list reference from cache
                        if type(param) is dict and 'ref' in param.keys():
                            newAction = await parse_list(param["field"], param["ref"])
                            newAction['object'] = 'action'
                            newAction['id'] = f"{parentId}-{newAction['vmanage-id']}"
                            newAction['children'] = None
                            newAction['parent'] = parentId
                            newAction = newAction | {
                                'color': '#adb5bd',
                                'stroke': '#ebebeb',
                                'size': 7,
                            }
                        # No list reference, build-up object
                        else:
                            name = ''
                            for e in param.keys():
                                name = f'{name} [ {param[e]} ]'
                            newAction = {
                                'id': f"{parentId}-action-{action['type']}",
                                'vmanage-id': None,
                                'object': 'action',
                                'type': action['type'],
                                'name': name,
                                'description': f"{action['type']}: {name}",
                                'children': None,
                                'parent': parentId,
                                'color': '#adb5bd',
                                'stroke': '#ebebeb',
                                'size': 7,
                            }
                        # Add to action list
                        newActions.append(newAction)
                else:
                    newAction = {
                        'id': f"{parentId}-action-{action['type']}",
                        'vmanage-id': None,
                        'object': 'action',
                        'type': action['type'],
                        'name': action['type'],
                        'description': action['type'],
                        'children': None,
                        'parent': parentId,
                        'color': '#adb5bd',
                        'stroke': '#ebebeb',
                        'size': 7,
                    }
                    # Add to action list
                    newActions.append(newAction)
            # return parsed value
            return newActions

        # Parse base action
        def parse_base_action(action, parentId):
            color = None
            match action:
                case 'accept':
                    color = "#00bc8c"  # green
                case 'pass':
                    color = "#00bc8c"  # green
                case 'reject':
                    color = "#e74c3c"  # red
                case 'inspect':
                    color = "#f39c12"  # orange
                case 'drop':
                    color = "#e74c3c"  # red
                case _:
                    color = "#3498db"  # blue
            base_action = {
                'id': f"{parentId}-baseAction",
                'vmanage-id': None,
                'object': 'action',
                'type': 'default',
                'name': action,
                'description': action,
                'parent': parentId,
                'children': None,
                'color': color,
                'stroke': '#ebebeb',
                'size': 7,
            }
            return base_action

        # Parse default action
        def parse_default_action(action, parentId):
            color = None
            match action['type']:
                case 'accept':
                    color = "#00bc8c"  # green
                case 'pass':
                    color = "#00bc8c"  # green
                case 'reject':
                    color = "#e74c3c"  # red
                case 'inspect':
                    color = "#f39c12"  # orange
                case 'drop':
                    color = "#e74c3c"  # red
                case _:
                    color = "#3498db"  # blue
            defaultAction = {
                'id': f"{parentId}-defaultAction",
                'vmanage-id': None,
                'object': 'sequence',
                'type': 'implicit',
                'name': 'Default action',
                'description': 'implicit default action',
                'parent': parentId,
                'color': '#3498db',
                'stroke': '#ebebeb',
                'size': 8,
                'children': [
                    {
                        'id': f"{parentId}-defaultAction-action",
                        'object': 'action',
                        'type': 'default',
                        'name': action['type'],
                        'description': action['type'],
                        'parent': f"{parentId}-defaultAction",
                        'children': None,
                        'color': color,
                        'stroke': '#ebebeb',
                        'size': 7,
                    }
                ]
            }
            return defaultAction

        # Get policy data
        try:
            policy = await self.policyData()
        except VmanageError as error:
            return {'error': str(error)}
        policy = parse_policy(policy, id, flavor)
        # Loop on assembly data
        newDefinitions = []
        try:
            tasks   = [self.policyDefinition(assembly['definitionId'], assembly['type']) for assembly in policy['assembly']]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except VmanageError as error:
            return {'error': str(error)}
        i = 0
        for assembly in policy['assembly']:
            # Get definition details
            definition = results[i]
            i = i + 1
            newDefinition = parse_definition(definition, policy['id'])                
            # Special case zoneBasedFW : copy entries from definition to assembly
            # create one entry per object
            if 'definition' in definition.keys() and 'entries' in definition['definition'].keys():
                oldArray = definition['definition']['entries']
                newArray = []
                for e in oldArray:
                    for k in e.keys():
                        newArray.append({k: e[k]})
                assembly['entries'] = newArray
                # Parse entries
            if 'entries' in assembly.keys():
                newDefinition['entries'] = await parse_entries(assembly['entries'], policy['id'])
                # Update description
                props = newDefinition['entries']
                desc = f"{newDefinition['description']}\n"
                for entry in props:
                    if 'direction' in entry:
                        desc += f"direction: {entry['direction']}\n"
                    if 'name' in entry:
                        desc += f"name: {entry['name']}\n"
                    if 'lists' in entry:
                        desc += f"{entry['lists']['type']}: {entry['lists']['name']}\n"
                        desc += f"{entry['lists']['description']}\n"
                newDefinition['description'] = desc
            # Parse sequences
            newSequences = []
            if 'sequences' in definition.keys():
                # Loop on sequences
                for sequence in definition['sequences']:
                    # Init sequence object
                    newSequence = parse_sequence(sequence, newDefinition['id'])
                    # Parse match conditions
                    if 'match' in sequence.keys():
                        newSequence['children'] += await parse_match(sequence['match']['entries'], newSequence['id'])
                    # Parse actions
                    if 'actions' in sequence.keys():
                        newSequence['children'] += await parse_action(sequence['actions'], newSequence['id'])
                    # Parse default action
                    if 'baseAction' in sequence.keys():
                        newSequence['children'].append(parse_base_action(sequence['baseAction'], newSequence['id']))
                    # Append policy sequence
                    newSequences.append(newSequence)
            # Parse default action
            if 'defaultAction' in definition.keys():
                defaultAction = parse_default_action(definition['defaultAction'], newDefinition['id'])
                newSequences.append(defaultAction)
            # Parse collectors (cflowd)
            if 'definition' in definition.keys() and 'collectors' in definition['definition'].keys():
                newSequences += parse_collectors(definition['definition']['collectors'], newDefinition['id'])
            # Parse qosMAP definition
            if 'definition' in definition.keys() and 'qosSchedulers' in definition['definition'].keys():
                newSequences += await parse_schedulers(definition['definition']['qosSchedulers'], newDefinition['id'])
            # Add sequences to definition
            newDefinition['children'] = newSequences
            # Append definition
            newDefinitions.append(newDefinition)
        # Finalize policy object
        policy['children'] = newDefinitions
        del policy['assembly']
        # return
        return policy
