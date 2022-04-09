from flask import render_template, request, redirect, url_for, jsonify, abort, g
from flask_cas import login_required
from app import app, db, scraper, cas
from app.models import User, Organization, Key
from app.util import to_json, succ, fail

import datetime
import time


@app.before_request
def store_user():
    if request.method != 'OPTIONS':
        if cas.username:
            g.user = User.query.get(cas.username)
            timestamp = int(time.time())
            if not g.user:
                # If this is the first user (probably local run), there's been no chance to
                # run the scraper yet, so give them admin to prevent an instant 403.
                is_first_user = User.query.count() == 0
                g.user = User(id=cas.username,
                              registered_on=timestamp,
                              admin=is_first_user)
                db.session.add(g.user)
            g.user.last_seen = timestamp
            try:
                print(g.person.first_name + ' ' + g.person.last_name)
            except AttributeError:
                print('Could not render name.')
            db.session.commit()


@app.route('/')
def index():
    if not cas.username:
        return render_template('splash.html')
    return render_template('index.html')


@app.route('/scraper', methods=['GET', 'POST'])
@login_required
def scrape():
    if not g.user.admin:
        abort(403)
    if request.method == 'GET':
        return render_template('scraper.html')
    payload = request.get_json()
    scraper.scrape.apply_async(args=[payload['yaleconnect_cookie']])
    return '', 200


@app.route('/keys', methods=['GET'])
@login_required
def get_keys():
    keys = Key.query.filter_by(user_id=g.user.id,
                               deleted=False).all()
    return to_json(keys)


@app.route('/keys', methods=['POST'])
@login_required
def create_key():
    payload = request.get_json()
    key = g.user.create_key(payload['description'])
    db.session.add(key)
    db.session.commit()
    return to_json(key)


"""
@app.route('/keys/<key_id>', methods=['POST'])
@login_required
def update_key(key_id):
    pass
"""


@app.route('/keys/<key_id>', methods=['DELETE'])
@login_required
def delete_key(key_id):
    key = Key.query.get(key_id)
    if key.user_id != g.user.id:
        return fail('You may not delete this key.', 403)
    key.deleted = True
    db.session.commit()
    return succ('Key deleted.')
