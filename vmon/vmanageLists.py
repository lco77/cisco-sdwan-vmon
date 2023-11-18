from flask import (Blueprint, render_template)

from vmonAuth import login_required

# from vmon.vmanage import (VmanageError, vmanage, vedge)

# Blueprints
bp = Blueprint('lists', __name__, url_prefix='/lists')


# index view
@bp.route('/', methods=('GET',))
@login_required
def index():
    # render view
    return render_template('lists/index.html')
