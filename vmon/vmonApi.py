# from logging import BufferingFormatter
from flask import (current_app, g, Blueprint, request, url_for, session, jsonify, json, make_response)
# from werkzeug.exceptions import abort
from vmonAuth import login_required
from vmanageApi import (VmanageError, vmanage, vedge, deviceTemplate)
from vmonJobs import (vmonQueue, rq_test)
import re

# import asyncio
# import httpx

# Blueprints
################################################################################################
bp = Blueprint('api', __name__, url_prefix='/api')


# CRUD API
################################################################################################
# API documentation
@bp.route('/', methods=('GET',))
@login_required
def crud_doc():
    return current_app.config['api']


# CRUD endpoint
@bp.route('/<string:object>/<string:action>', methods=(['GET', 'PUT', 'POST', 'DELETE']))
async def crud_api(action, object):
    # session error
    if g.user is None or not 'vid' in session.keys():
        return {'error': True, 'message': 'Session error'}
    # actions
    actions = ['index', 'read', 'create', 'edit', 'delete']
    if not action in actions:
        return {'error': True, 'message': f'Invalid action {action}'}
    # get URL parameters
    args = request.args.to_dict()
    # get payload
    try:
        payload = json.loads(request.data)
    except:
        payload = None
    # route request
    try:
        s = vmanage(session['vid'])
        r = await s.crud(action, object, args, payload)
    except VmanageError as error:
        return {'error': True, 'message': str(error)}, 400
    return r, 200


# RQ Jobs monitor
@bp.route('/jobs', methods=('GET',))
async def jobs():
    # session error
    if g.user is None:
        return {'error': True, 'message': 'Session error'}
    # Get data
    try:
        q = vmonQueue('vmonJobs')
        q.add_job(rq_test, a=1, b=2, c=3, d=4)
        registries = q.get_registries()
    except:
        pass
    # Process result
    result = {'jobs': []}
    for registry in registries:
        result[registry] = [job for job in registries[registry].get_job_ids()]
    return result


# Get device list
# - Get data from multiple vmanage endpoints & merge into one device list
# - Columns and device state info are customized
################################################################################################
@bp.route('/devices', methods=('GET',))
async def devices():
    # session error
    if g.user is None or not 'vid' in session.keys():
        return {'error': True, 'message': 'Session error'}
    # Get data
    try:
        s = vmanage(session['vid'])
        objects = [
            {'action': 'index', 'object': 'device', 'args': None, 'payload': None},
            {'action': 'read', 'object': 'system_device', 'args': {'deviceCategory': 'vedges'}, 'payload': None},
            {'action': 'read', 'object': 'system_device', 'args': {'deviceCategory': 'controllers'}, 'payload': None},
            {'action': 'index', 'object': 'device_hardwarehealth_detail', 'args': None, 'payload': None},
        ]
        (d, v, c, h) = await s.cruds(objects)
    except VmanageError as error:
        return {'error': str(error)}
    # Init response object
    response = {}
    # Define columns
    columns = [
        {'title': "Hostname", 'data': "host-name", 'visible': True},
        {'title': "State", 'data': "state", 'visible': True},
        {'title': "System IP", 'data': "system-ip", 'visible': True},
        {'title': "Site ID", 'data': "site-id", 'visible': True},
        {'title': "Groups", 'data': "device-groups", 'visible': True},
        {'title': "Version", 'data': "version", 'visible': True},
        {'title': 'Template', 'data': 'template', 'visible': True},
        {'title': "Reachability", 'data': "reachability", 'visible': True},
        {'title': 'Config Status', 'data': 'configStatusMessage', 'visible': True},
        {'title': 'Cert Status', 'data': 'validity', 'visible': True},
        {'title': "CTRL", 'data': "controlConnections", 'type': 'html-num', 'visible': True},
        {'title': "BFD", 'data': "bfdSessions", 'type': 'html-num', 'visible': True},
        {'title': 'OMP', 'data': 'ompPeers', 'type': 'html-num', 'visible': True},
        {'title': 'CPU', 'data': 'cpuLoadDisplay', 'type': 'html-num', 'visible': True},
        {'title': 'MEM', 'data': 'memUsageDisplay', 'type': 'html-num', 'visible': True},
        {'title': 'Actions', 'data': 'dummy', 'visible': True},
        {'title': "UUID", 'data': "uuid", 'visible': False},
        {'title': 'Template ID', 'data': 'templateId', 'visible': False},
        {'title': 'Device Type', 'data': 'deviceType', 'visible': False},
        {'title': "Device Model", 'data': "deviceModel", 'visible': False},
        {'title': "platformFamily", 'data': "platformFamily", 'visible': False},
    ]
    response['columns'] = columns
    # Rebuild data set & process state
    response['data'] = []
    # Extract non-synced devices ("inactive")
    unsynced = {'columns': v['header']['columns'], 'data': []}
    for e in v['data']:
        if not 'system-ip' in e.keys():
            unsynced['data'].append(e)
    # Loop on device data
    for device in d['data']:
        # element = {}
        element = device
        edge = {}
        controller = {}
        health = {}
        # Match device with edge data
        for e in v['data']:
            if e['uuid'] == device['uuid']:
                edge = e
        # Match device with controller data
        for e in c['data']:
            if e['uuid'] == device['uuid']:
                e['deviceType'] = 'controller'
                controller = e
        # Match device with health data
        for e in h['data']:
            if e['uuid'] == device['uuid']:
                health = e
        # Merge data
        for e in [edge, controller, health]:
            for col in columns:
                if col['data'] in e.keys():
                    element[col['data']] = e[col['data']]
        # add link to device page
        element['link'] = url_for('devices.device', id=device['deviceId'])
        # compute device state
        if 'state' in device.keys():
            del device['state']
        if 'uptime-date' in device.keys():
            del device['uptime-date']
        # Need to rework how state is computed (cosmetic but important)
        if device['validity'] != 'Valid':
            element['state'] = 'red'
        if 'reachability' in device.keys() and device['reachability'] != 'reachable':
            element['state'] = 'red'
        elif 'bfdSessions' in device.keys():
            if '(' in device['bfdSessions']:
                element['state'] = 'orange'
            else:
                element['state'] = 'green'
        else:
            element['state'] = 'green'
        # push device info to data set
        response['data'].append(element)
        response['inactive'] = unsynced
    # send data
    return response


# Device - available real-time monitor objects by device personality
################################################################################################
@bp.route('/device/actions/<string:personality>', methods=('GET',))
async def device_actions_list(personality):
    # session error
    if g.user is None or not 'vid' in session.keys():
        return {'error': True, 'message': 'Session error'}
    if not personality in ["vmanage", "vedge-vbond", "vedge", "vsmart"]:
        return {'error': 'Parameter "personality" is required'}
    # Get monitor actions
    try:
        s = vmanage(session['vid'])
        r = await s.crud('index', 'client_monitor_device_options', {'isCiscoDevice': True}, None)
    except VmanageError as error:
        return {'error': str(error)}
    # Parse actions
    actions = []
    for action in r['data']:
        if personality in action['personality']:
            category = action['name']
            children = []
            for child in action['children']:
                object = child['uri'].replace('dataservice/', '').replace('/', '_').replace('-', '_').lower()
                name = f"{action['name']} {child['name']}"
                children.append({'name': name, 'object': object, 'action': 'read'})
            actions.append({'category': category, 'children': children})
    return {'data': actions}


# Device config
# - type = sdwan or running
################################################################################################
@bp.route('/device/config/<string:deviceid>', methods=('GET',))
async def device_config(deviceid):
    # session error
    if g.user is None or not 'vid' in session.keys():
        return {'error': True, 'message': 'Session error'}
    type = request.args.get('type')
    if not type in ['sdwan', 'running']:
        return {'error': 'Wrong parameter'}
    # Init vedge object
    try:
        s = vmanage(session['vid'])
        o = vedge(s, deviceid)
        r = await o.getConfig(type)
    except VmanageError as error:
        return {'error': str(error)}
    return r


# Device config (for devices with a / in UUID)
# - type = sdwan or running
################################################################################################
@bp.route('/device/config/<string:deviceid>/<string:deviceid2>', methods=('GET',))
async def device_config_split(deviceid, deviceid2):
    # session error
    if g.user is None or not 'vid' in session.keys():
        return {'error': True, 'message': 'Session error'}
    deviceid = f'{deviceid}/{deviceid2}'
    type = request.args.get('type')
    if not type in ['sdwan', 'running']:
        return {'error': 'Parameter "type" is required'}
    # Init vedge object
    try:
        s = vmanage(session['vid'])
        o = vedge(s, deviceid)
        r = await o.getConfig(type)
    except VmanageError as error:
        return {'error': str(error)}
    return r


# BFD Edge Bundling Diagram
# - extracts topology data for all vedge devices before handing it over to client
# - uses an object cache to reduce API queries to vManage
# params:
#         deviceId={system-ip} => restrict scope to one vedge device
################################################################################################
@bp.route('/bfd/topology', methods=('GET',))
async def bfdTopology():
    # session error
    if g.user is None or not 'vid' in session.keys():
        return {'error': True, 'message': 'Session error'}

    # define get_devices function
    ############################################################################################
    async def get_devices():
        list = []
        # r = s.get_by_type('device')
        try:
            r = await s.crud('index', 'device', None, None)
        except VmanageError as error:
            raise VmanageError(str(error))
        # Compute device list
        for e in r['data']:
            # Skip NFVIS and controllers
            if e['device-type'] != 'vedge' or re.match('^vedge-nfvis', e['device-model']):
                continue
            # Add device to device list
            list.append({
                'id': e['deviceId'],
                'name': e['host-name'],
                'type': e['device-type'],
                'site': e['site-id'],
                'group': e['device-groups'][0],
            })
        # Return device list
        return list

    # define get_tlocs function
    ############################################################################################
    def parse_tlocs(tlocs):
        list = []
        for e in tlocs['data']:
            list.append({
                'color': e['color'],
                'state': e['operation-state'],
                'preference': e['preference'],
                'restrict': e['restrict-str'],
            })
            # Return tloc list
        return list

    async def get_tlocs(id):
        list = []
        # r = s.get_by_id('tlocs',id)
        try:
            r = await s.crud('read', 'device_control_synced_waninterface', {'deviceId': id}, None)
        except VmanageError as error:
            raise VmanageError(str(error))
        # Compute tloc list
        for e in r['data']:
            list.append({
                'color': e['color'],
                'state': e['operation-state'],
                'preference': e['preference'],
                'restrict': e['restrict-str'],
            })
            # Return tloc list
        return list

    # define get_sessions function
    ############################################################################################
    def parse_sessions(sessions):
        list = []
        for e in sessions['data']:
            list.append({
                'source': e['vmanage-system-ip'],
                'target': e['system-ip'],
                'state': e['state'],
                'local-color': e['local-color'],
                'remote-color': e['color'],
            })
            # Return sessions list
        return list

    async def get_sessions(id):
        list = []
        # r = s.get_by_id('bfdsessions',id)
        try:
            r = await s.crud('read', 'device_bfd_synced_sessions', {'deviceId': id}, None)
        except VmanageError as error:
            raise VmanageError(str(error))
        # Compute session list
        for e in r['data']:
            list.append({
                'source': e['vmanage-system-ip'],
                'target': e['system-ip'],
                'state': e['state'],
                'local-color': e['local-color'],
                'remote-color': e['color'],
            })
            # Return sessions list
        return list

    # define make_node function
    ############################################################################################
    def make_node(device, tloc):
        # Create new node
        node = {
            'id': re.sub('\.', '-', f"{device['id']}_{tloc['color']}"),
            'name': f"{device['name']} [{tloc['color']}]",
            'hostname': device['name'],
            'systemIp': device['id'],
            'site': device['site'],
            'group': device['group'],
            'color': tloc['color'],
            'preference': tloc['preference'],
            'restrict': tloc['restrict'],
            'state': tloc['state'],
            'bfdPeers': []
        }
        return node

    # define make_link function
    ############################################################################################
    def make_link(bfd):
        link = {
            'id': re.sub('\.', '-', f"{bfd['source']}_{bfd['local-color']}-{bfd['target']}_{bfd['remote-color']}"),
            'source': re.sub('\.', '-', f"{bfd['source']}_{bfd['local-color']}"),
            'target': re.sub('\.', '-', f"{bfd['target']}_{bfd['remote-color']}"),
            'sourceSystemIp': bfd['source'],
            'targetSystemIp': bfd['target'],
            'sourceColor': bfd['local-color'],
            'targetColor': bfd['remote-color'],
            'state': bfd['state']
        }
        return link

    # main function
    ############################################################################################
    # Init nodes and links
    nodes = []
    links = []
    # Init cache
    bfdCache = {}
    tlocCache = {}
    # Get vEdge list
    try:
        s = vmanage(session['vid'])
        devices = await get_devices()
    except VmanageError as error:
        return {'error': str(error)}
    # Get deviceId param, if any
    deviceId = request.args.get('deviceId')
    # Validate it
    if deviceId:
        if not re.match('^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', deviceId):
            return {"error": "wrong parameter"}
        else:
            isValid = False
            for device in devices:
                if device['id'] == deviceId:
                    isValid = True
            if not isValid:
                return {"error": "wrong parameter"}
    # Prepare async tasks
    objects = []
    for device in devices:
        objects.append(
            {'action': 'read', 'object': 'device_control_synced_waninterface', 'args': {'deviceId': device['id']},
             'payload': None})
        objects.append({'action': 'read', 'object': 'device_bfd_synced_sessions', 'args': {'deviceId': device['id']},
                        'payload': None})
    # Fire async tasks
    try:
        results = await s.cruds(objects)
    except VmanageError as error:
        return {'error': str(error)}
    i = 0
    # Make TLOC inventory
    for device in devices:
        tlocs = parse_tlocs(results[i])
        sessions = parse_sessions(results[i + 1])
        i = i + 2
        tlocCache[device['id']] = tlocs
        bfdCache[device['id']] = sessions
        # Assemble TLOC inventory
        for tloc in tlocs:
            nodes.append(make_node(device, tloc))

    # Case 1: no deviceId supplied as request parameter
    if not deviceId:
        for node in nodes:
            # Loop on BFD session cache for this node
            for bfd in bfdCache[node['systemIp']]:
                # Focus on BFD sessions matching with local TLOC color
                if bfd['local-color'] == node['color']:
                    # Some inconsistencies may exist as we query vManage cache; so make sure the remote TLOC actually exist before creating a new link
                    for target in nodes:
                        if bfd['target'] == target['systemIp']:
                            # Add link to list
                            link = make_link(bfd)
                            links.append(link)
                            # Add target node as child of current node
                            node['bfdPeers'].append({'id': link['target'], 'state': link['state']})

    # Case 2: deviceId supplied as request parameter
    if deviceId and deviceId in bfdCache.keys():
        # Loop on local BFD sessions
        for bfd in bfdCache[deviceId]:
            # Match BFD target with an existing vEdge device
            for device in devices:
                if device['id'] == bfd['target']:
                    # Add link to list
                    link = make_link(bfd)
                    links.append(link)
                    # Get TLOCs of remote peer
                    if bfd['target'] in tlocCache.keys():
                        tlocs = tlocCache[bfd['target']]
                    else:
                        try:
                            tlocs = await get_tlocs(bfd['target'])
                        except VmanageError as error:
                            return {'error': str(error)}
                        tlocCache[bfd['target']] = tlocs
                    # Extend TLOC inventory with TLOCs from remote peer
                    for tloc in tlocs:
                        # Match on SystemIP and TLOC color and avoid duplicates
                        isNew = True
                        for node in nodes:
                            if node['systemIp'] == bfd['target'] and node['color'] == tloc['color']:
                                isNew = False
                        if isNew:
                            nodes.append(make_node(device, tloc))
                    # Get BFD sessions of remote peer
                    if bfd['target'] in bfdCache.keys():
                        sessions = bfdCache[bfd['target']]
                    else:
                        try:
                            sessions = await get_sessions(bfd['target'])
                        except VmanageError as error:
                            return {'error': str(error)}
                        bfdCache[bfd['target']] = sessions
                    # Loop on BFD sessions of remote peer
                    for remoteBfd in sessions:
                        # Add link from remote peer to local peer
                        if remoteBfd['target'] == deviceId:
                            link = make_link(remoteBfd)
                            links.append(link)
    # Return edges
    return {'nodes': nodes, 'links': links}


# BFD Arc Diagram
# extract topology data for all vedge devices before handing it over to d3.js
# params:
#         deviceId={system-ip} -> Extract topology data for one vedge device
################################################################################################
@bp.route('/bfd/status', methods=('GET',))
async def bfdStatus():
    # session error
    if g.user is None or not 'vid' in session.keys():
        return {'error': True, 'message': 'Session error'}

    # define make_node function
    ############################################################################################
    def make_node(device):
        # Create new node
        node = {
            'id': device['deviceId'],
            'name': device['host-name'],
            'type': device['device-type'],
            'site': device['site-id'],
            'group': device['device-groups'][0],
        }
        return node

    # define make_link function
    ############################################################################################
    def make_link(bfd):
        link = {
            'source': bfd['vmanage-system-ip'],
            'target': bfd['system-ip'],
            'state': bfd['state'],
            'color': bfd['local-color'],
        }
        return link

    # main function
    ############################################################################################
    # Init response
    data = {
        'nodes': [],
        'links': []
    }
    # Get vEdge list
    try:
        s = vmanage(session['vid'])
        r1 = await s.crud('index', 'device', None, None)
    except VmanageError as error:
        return {'error': str(error)}
    # Loop through device list and build-up node list
    for element in r1['data']:
        # Skip NFVIS and controllers
        if element['device-type'] != 'vedge' or re.match('^vedge-nfvis', element['device-model']):
            continue
        # Add this device to node list
        data['nodes'].append(make_node(element))
    # Prepare async requests
    objects = [
        {'action': 'read', 'object': 'device_bfd_synced_sessions', 'args': {'deviceId': node['id']}, 'payload': None}
        for node in data['nodes']]
    try:
        results = await s.cruds(objects)
    except VmanageError as error:
        return {'error': str(error)}
    # Process results
    for result in results:
        for bfdsession in result['data']:
            # Safety check to ensure that target belongs to node list (as we query vmanage's cache, some inconsistencies may exist)
            for target in data['nodes']:
                if target['id'] == bfdsession['system-ip']:
                    # Now we can safely add without pointing to a missing target
                    data['links'].append(make_link(bfdsession))
    # Loop through node list and build up link list
    # i = 0
    # for node in data['nodes']:
    #     # Fetch its BFD sessions
    #     r2 = results[i]
    #     i = i + 1
    #     # Add sessions to link list
    #     for bfdsession in r2['data']:
    #         # Safety check to ensure that target belongs to node list (as we query vmanage's cache, some inconsistencies may exist)
    #         for target in data['nodes']:
    #             if target['id'] == bfdsession['system-ip']:
    #                 # Now we can safely add without pointing to a missing target
    #                 data['links'].append(make_link(bfdsession))
    return data


# Template Tree
# - get template info, resolve dependencies & return hierachy object
################################################################################################
@bp.route('/device_template/<string:id>/tree', methods=('GET',))
async def device_template_tree(id):
    # session error
    if g.user is None or not 'vid' in session.keys():
        return {'error': True, 'message': 'Session error'}
    try:
        s = vmanage(session['vid'])
        o = deviceTemplate(s, id)
        r = await o.hierarchy()
    except VmanageError as error:
        return {"error": str(error)}
    return r


# Device Template Attachments
# - get template attachments
################################################################################################
@bp.route('/device_template/<string:id>/attachments', methods=('GET',))
async def device_template_attachments(id):
    # session error
    if g.user is None or not 'vid' in session.keys():
        return {'error': True, 'message': 'Session error'}
    # Get object data
    try:
        s = vmanage(session['vid'])
        o = deviceTemplate(s, id)
        r = await o.attachments()
    except VmanageError as error:
        return {"error": str(error)}
    return r


# Device Template Inputs
# - get template input definition
################################################################################################
@bp.route('/device_template/<string:id>/input', methods=('GET',))
async def device_template_input(id):
    # session error
    if g.user is None or not 'vid' in session.keys():
        return {'error': True, 'message': 'Session error'}
    # Open vmanage session
    try:
        s = vmanage(session['vid'])
        o = deviceTemplate(s, id)
        r = await o.values()
    except VmanageError as error:
        return {"error": str(error)}
    return r


# Device Template Inputs per device
# - get template input value for one or more devices
################################################################################################
@bp.route('/device_template/<string:id>/input/<string:uuid>', methods=('GET',))
async def device_template_input_per_device(id, uuid):
    # session error
    if g.user is None or not 'vid' in session.keys():
        return {'error': True, 'message': 'Session error'}
    # Open vmanage session
    try:
        s = vmanage(session['vid'])
        o = deviceTemplate(s, id)
        r = await o.values(uuid)
    except VmanageError as error:
        return {"error": str(error)}
    return r


# Extra route for devices containing / in their uuid (thanks cisco)
@bp.route('/device_template/<string:id>/input/<string:uuid>/<string:uuid2>', methods=('GET',))
async def device_template_input_per_device_split(id, uuid, uuid2):
    # session error
    if g.user is None or not 'vid' in session.keys():
        return {'error': True, 'message': 'Session error'}
    # Open vmanage session
    try:
        s = vmanage(session['vid'])
        o = deviceTemplate(s, id)
        r = await o.values(uuid + '/' + uuid2)
    except VmanageError as error:
        return {"error": str(error)}
    return r


# Device Template CSV
# - get template input value for one or more devices
################################################################################################
@bp.route('/device_template/<string:id>/csv/<string:uuid>', methods=('GET',))
async def device_template_csv(id, uuid):
    # session error
    if g.user is None or not 'vid' in session.keys():
        return {'error': True, 'message': 'Session error'}
    # Open vmanage session
    try:
        s = vmanage(session['vid'])
        o = deviceTemplate(s, id)
        r = await o.csv(uuid)
    except VmanageError as error:
        return {"error": str(error)}
    response = make_response(r)
    response.headers["Content-Type"] = "text/csv"
    return response


# Device Template Attach
# - attach device to template using values
################################################################################################
@bp.route('/device_template/<string:id>/attach', methods=('POST',))
async def device_template_attach(id):
    # session error
    if g.user is None or not 'vid' in session.keys():
        return {'error': True, 'message': 'Session error'}
    payload = request.get_json()
    # Open vmanage session
    try:
        s = vmanage(session['vid'])
        o = deviceTemplate(s, id)
        r = await o.attach(payload)
    except VmanageError as error:
        return {"error": str(error)}
    redirect = url_for('tasks.index')
    return {'data': r, 'redirect': redirect}
