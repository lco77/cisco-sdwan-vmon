from flask import (g, Blueprint, render_template, session)

from vmanageApi import (VmanageError, vmanage, vedge)
from vmonAuth import login_required

# Blueprints
bp = Blueprint('devices', __name__, url_prefix='/devices')


# index view
@bp.route('/', methods=('GET',))
@login_required
def index():
    # render view
    return render_template('devices/index.html')


# device view
@bp.route('/<string:id>', methods=('GET',))
async def device(id):
    # session error
    if g.user is None or not 'vid' in session.keys():
        return {'error': True, 'message': 'Session error'}
    try:
        s = vmanage(session['vid'])
        o = vedge(s, id)
        details = await o.details()
        # s.close()
    except VmanageError as error:
        return {'error': str(error)}
    # print(details)
    return render_template('devices/device.html', details=details)
