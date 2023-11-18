from flask import (Blueprint)

from vmonAuth import login_required

# TODO
# implement simple DOH server to enable client-side DNS resolutions

# Blueprints
bp = Blueprint('doh', __name__, url_prefix='/doh')


# index view
@bp.route('/<string:type>/<string:value>', methods=('GET',))
@login_required
def index(type, value):
    # render view
    return {'data': None}
