from flask import (Blueprint, render_template)

from vmonAuth import login_required

# Blueprints
bp = Blueprint('alarms', __name__, url_prefix='/alarms')


# index view
@bp.route('/', methods=('GET',))
@login_required
def index():
    return render_template('alarms/index.html')
