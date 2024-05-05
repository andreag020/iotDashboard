import logging
import os
from flask import Flask, render_template, request, redirect, url_for
from dotenv import load_dotenv
from model.app_model import get_tuya_devices, get_firestore_devices
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

login_manager = LoginManager()
login_manager.init_app(app)


class User(UserMixin):
    pass


users = {'foo': {'password': 'bar'}}


@login_manager.user_loader
def user_loader(username):
    if username not in users:
        return

    user = User()
    user.id = username
    return user


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    username = request.form['username']
    if username in users and request.form['password'] == users[username]['password']:
        user = User()
        user.id = username
        login_user(user)
        return redirect(url_for('dashboard'))

    return 'Bad login'


@app.route('/protected')
@login_required
def dashboard():
    devices_tuya = get_tuya_devices()
    devices_db = get_firestore_devices()
    # logging.info("Response: %s", devices_tuya)
    return render_template('index.html', devices_tuya=devices_tuya, devices_db=devices_db)
    # return 'Logged in as: ' + current_user.id


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()
    return 'Logged out'


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
