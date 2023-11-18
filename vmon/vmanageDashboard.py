from flask import (Blueprint, g, render_template, request)

from vmanageApi import (VmanageError, vmanage)
from vmonAuth import login_required
from vmonModels import (db, Server)

# Blueprints
bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')


# index view to return base layout + connections info
@bp.route('/', methods=('GET',))
@login_required
def index():
    # Get vManage connections
    try:
        connections = db.session.query(Server).filter_by(user_id=g.user.id).all()
    except:
        return {'error': 'DB error'}
    # render view
    return render_template('dashboard/index.html', connections=connections)


# Get data from vManage server without using session['vid'] from the user session
# - used for dashboarding multiple vmanage servers on the same page
# - requires [object] parameter with a valid "vmanage.get_list" endpoint
@bp.route('/data/<string:id>', methods=('GET',))
async def data(id):
    # session error
    if g.user is None:
        return {'error': True, 'message': 'Session error'}
    map_endpoints = {
        'inventory_health': {'object': 'device_vedgeinventory_summary', 'action': 'index', 'params': None},
        'certificate_health': {'object': 'certificate_stats_summary', 'action': 'index', 'params': None},
        'control_health': {'object': 'device_control_count', 'action': 'index', 'params': {'isCached': True}},
        'vedge_health': {'object': 'device_hardwarehealth_summary', 'action': 'read',
                         'params': {'isCached': True, 'vpnId': '0'}},
        'vmanage_health': {'object': 'clustermanagement_health_summary', 'action': 'index', 'params': None},
        'site_health': {'object': 'device_bfd_sites_summary', 'action': 'read',
                        'params': {'isCached': True, 'vpnId': '0'}},
        'reachability_health': {'object': 'network_connectionssummary', 'action': 'index', 'params': None},
    }
    # Check for object param
    req_object = request.args.get('object')
    if not (req_object and req_object in map_endpoints.keys()):
        return {'error': 'permission denied'}
    object = map_endpoints[req_object]['object']
    action = map_endpoints[req_object]['action']
    params = map_endpoints[req_object]['params']
    # Get vManage connection
    try:
        c = db.session.query(Server).filter_by(user_id=g.user.id, id=id).first()
        if c is None:
            return {'error': 'permission denied'}
        s = vmanage(c.id)
        r = await s.crud(action, object, params, None)
    except VmanageError as error:
        return {'error': str(error)}
    return r
