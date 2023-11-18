from flask import (Blueprint, render_template)

from vmonAuth import login_required

# Blueprint definition
bp = Blueprint('templates', __name__, url_prefix='/templates')


# index view
@bp.route('/', methods=('GET',))
@login_required
def index():
    return render_template('templates/index.html')


# template view
# TODO: add support for network design template
@bp.route('/<string:object>/<string:id>', methods=('GET',))
@login_required
def show(object, id):
    if object == "device_template":
        return render_template('templates/device_template.html', id=id)
    return {'message': 'TODO'}
