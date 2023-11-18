from flask import (Blueprint, flash, g, redirect, render_template, request, url_for, session)
from werkzeug.exceptions import abort

from vmanageApi import VmanageError, vmanage
from vmonAuth import login_required
from vmonForms import ServerForm
from vmonModels import db, Server

# Define Blueprint
bp = Blueprint('connections', __name__, url_prefix='/connections')


# List connections
@bp.route('/', methods=('POST', 'GET'))
@login_required
def index():
    try:
        connections = db.session.query(Server).filter_by(user_id=g.user.id).all()
    except:
        return {'error': 'DB error'}
    if request.method == 'GET':
        return render_template('connections/index.html', connections=connections)
    else:
        response = {'data': []}
        for c in connections:
            response['data'].append({'id': c.id, 'server': c.server, 'description': c.description})
        return response


# New connection
@bp.route('/create', methods=('POST', 'GET'))
@login_required
def create():
    form = ServerForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                connection = Server(user_id=g.user.id,
                                    server=request.form['server'].rstrip('/'),
                                    username=request.form['username'],
                                    password=request.form['password'],
                                    description=request.form['description'])
                connection.save()
            except:
                return {'error': 'DB error'}
            return redirect(url_for('connections.index'))
    return render_template('connections/create.html', form=form)


# Edit connection
@bp.route('/update/<int:id>', methods=('GET', 'POST'))
@login_required
def update(id):
    form = ServerForm()
    try:
        c = db.session.query(Server).filter_by(id=id).first()
    except:
        return {'error': 'DB error'}
    if g.user.id != c.user_id:
        return {'error': 'Permissions denied'}
    if request.method == 'POST':
        if form.validate_on_submit():
            c.server = request.form['server'].rstrip('/')
            c.username = request.form['username']
            c.password = request.form['password']
            c.description = request.form['description']
            try:
                db.session.commit()
            except:
                abort(400, {'message': 'DB error'})
            return redirect(url_for('connections.index'))
    return render_template('connections/update.html', connection=c, form=form)


# Delete connection
@bp.route('/delete/<int:id>', methods=('POST',))
@login_required
def delete(id):
    try:
        c = db.session.query(Server).filter_by(id=id).first()
    except:
        return {'error': 'DB error'}
    if c is None:
        flash('Could not delete connection.')
    elif g.user.id == c.user_id:
        try:
            c = db.session.query(Server).filter_by(id=id).first()
            db.session.delete(c)
            db.session.commit()
        except:
            return {'error': 'DB error'}
    else:
        flash('Could not delete connection.')
    return redirect(url_for('connections.index'))


# Test/Activate connection
@bp.route('/connect/<string:id>', methods=('GET', 'POST'))
@login_required
def connect(id):
    # Get vManage session
    try:
        c = db.session.query(Server).filter_by(id=id).first()
        if g.user.id != c.user_id:
            return {'error': 'permission denied'}
        s = vmanage(id)
        # s.close()
    except VmanageError as error:
        if request.method == 'GET':
            return render_template('connections/connect.html', connection=c, error=str(error))
        else:
            return {'error': str(error)}
    # GET -> Test connection
    if request.method == 'GET':
        return render_template('connections/connect.html', connection=c)
    # POST -> Activate connection
    session['vid'] = id
    session['vServer'] = c.server
    session['vUsername'] = c.username
    session['vDescription'] = c.description
    return {'message': 'Success',
            'redirect': url_for('devices.index'),
            'data': {
                'id': id,
                'server': c.server,
                'username': c.username,
                'description': c.description}
            }
