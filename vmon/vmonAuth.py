import functools

from flask import (Blueprint, g, redirect, render_template, request, session, url_for)

from vmonForms import (UserForm, PasswordForm)
# from werkzeug.security import check_password_hash, generate_password_hash
# from werkzeug.exceptions import abort
from vmonModels import (db, User)

# declare auth blueprint
bp = Blueprint('auth', __name__, url_prefix='/auth')


# Get user info from session
@bp.before_app_request
def load_logged_in_user():
    id = session.get('user_id')
    if id is None:
        g.user = None
    else:
        try:
            g.user = db.session.query(User).filter_by(id=id).first()
        except:
            return {'error': 'DB error'}


# Decorator to enforce login on selected views
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return view(**kwargs)
    return wrapped_view


# Create user
@bp.route('/register', methods=('GET', 'POST'))
def register():
    form = UserForm()
    error = None
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                user = User(username=request.form['username'])
                user.set_password(request.form['password'])
                user.save()
            except:
                error = f"User {request.form['username']} is already registered."
                return render_template('auth/register.html', form=form, error=error)
            return redirect(url_for("auth.login"))
    return render_template('auth/register.html', form=form, error=error)


# Login
@bp.route('/login', methods=('GET', 'POST'))
def login():
    form = UserForm()
    error = None
    if request.method == 'POST':
        if form.validate_on_submit():
            try:
                user = db.session.query(User).filter_by(username=request.form['username']).first()
            except:
                return {'error': 'DB error'}
            if user and user.check_password(request.form['password']):
                session.clear()
                session['user_id'] = user.id
                return redirect(url_for('dashboard.index'))
            else:
                error = 'Wrong password'
    return render_template('auth/login.html', form=form, error=error)


# Logout
@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))


# Change password
@bp.route('/profile/<int:id>', methods=('GET', 'POST'))
@login_required
def profile(id):
    form = PasswordForm()
    error = ''
    if request.method == 'POST':
        if form.validate_on_submit():
            # Check authorization + Early abort
            if g.user.id != id:
                error = f'{error}Permission denied.\n'
                return render_template('auth/profile.html', form=form, error=error)
            # Continue
            try:
                user = db.session.query(User).filter_by(id=id).first()
            except:
                return {'error': 'Failed to get user from DB'}
            # Validate old and new password against current DB password
            if not user.check_password(request.form['password']):
                error = f'{error}Wrong current password.\n'
            if user.check_password(request.form['password_new1']):
                error = f'{error}New password is identical to current password.\n'
            # All good, save new password
            if error == '':
                try:
                    user.set_password(request.form['password_new1'])
                    user.save()
                except:
                    return {'error': 'Failed to save password in DB'}
                return redirect(url_for('dashboard.index'))
    return render_template('auth/profile.html', id=id, form=form, error=error)


# Delete
@bp.route('/delete/<int:id>', methods=(['DELETE']))
@login_required
def delete(id):
    # Check authorization + Early abort
    if g.user.id != id:
        return {'error': 'Permission denied'}
    # Delete data
    try:
        user = db.session.query(User).filter_by(id=id).first()
        db.session.delete(user)
        db.session.commit()
    except:
        return {'error': 'DB delete error; try again'}
    # Clear session and redirect
    session.clear()
    return {'redirect': url_for('auth.register')}
