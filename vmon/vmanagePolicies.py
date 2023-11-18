from flask import (g, Blueprint, render_template, session)

from vmanageApi import (VmanageError, vmanage, vmanagePolicy)
# from werkzeug.exceptions import abort
from vmonAuth import login_required

# import json

# Blueprints
bp = Blueprint('policies', __name__, url_prefix='/policies')


# index view
@bp.route('/', methods=('GET',))
@login_required
def index():
    return render_template('policies/index.html')


# policy view
@bp.route('/<string:flavor>/<string:id>', methods=('GET',))
@login_required
def show(flavor, id):
    return render_template('policies/policy.html', flavor=flavor, policyId=id)


# Policy Tree Diagram
@bp.route('/<string:flavor>/<string:id>/tree', methods=('GET',))
async def tree(flavor, id):
    # session error
    if g.user is None or not 'vid' in session.keys():
        return {'error': True, 'message': 'Session error'}
    # Get policy data
    try:
        s = vmanage(session['vid'])
        o = vmanagePolicy(s, flavor, id)
        policy = await o.tree(id, flavor)
    except VmanageError as error:
        return {'error': str(error)}
    # s.close()
    return policy
