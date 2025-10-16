import os
import sys
from threading import Thread
from flask import Flask, render_template, session, redirect, url_for
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SubmitField
from wtforms.validators import DataRequired
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_mail import Mail, Message
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

import requests
from datetime import datetime

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hard to guess string'
app.config['SQLALCHEMY_DATABASE_URI'] =\
    'sqlite:///' + os.path.join(basedir, 'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['API_KEY'] = os.environ.get('API_KEY')
app.config['API_URL'] = os.environ.get('API_URL')
app.config['API_FROM'] = os.environ.get('API_FROM')
app.config['SENDGRID_API_KEY'] = os.environ.get('SENDGRID_API_KEY')

app.config['FLASKY_MAIL_SUBJECT_PREFIX'] = '[Flasky]'
app.config['FLASKY_ADMIN'] = os.environ.get('FLASKY_ADMIN')

bootstrap = Bootstrap(app)
moment = Moment(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
mail = Mail(app)


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __repr__(self):
        return '<Role %r>' % self.name


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))

    def __repr__(self):
        return '<User %r>' % self.username

def send_simple_message(to, subject, newUser):

    message = Mail(
        from_email=app.config['API_FROM'],
        to_emails=to,
        subject= app.config['FLASKY_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
        html_content="Novo usuário cadastrado: " + newUser)
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        # sg.set_sendgrid_data_residency("eu")
        # uncomment the above line if you are sending mail using a regional EU subuser
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e.message)


class NameForm(FlaskForm):
    name = StringField('What is your name?', validators=[DataRequired()])
    enviar_email = BooleanField('Deseja enviar e-mail para flaskaulasweb@zohomail.com?')
    submit = SubmitField('Submit')


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Role=Role)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


@app.route('/', methods=['GET', 'POST'])
def index():
    form = NameForm()
    enviar_email = form.enviar_email.data
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.name.data).first()
        if user is None:
            user = User(username=form.name.data)
            db.session.add(user)
            db.session.commit()
            session['known'] = False

            print('Verificando variáveis de ambiente: Server log do PythonAnyWhere', flush=True)
            print('FLASKY_ADMIN: ' + str(app.config['FLASKY_ADMIN']), flush=True)
            print('URL: ' + str(app.config['API_URL']), flush=True)
            print('api: ' + str(app.config['API_KEY']), flush=True)
            print('from: ' + str(app.config['API_FROM']), flush=True)
            print('to: ' + str([app.config['FLASKY_ADMIN'], "flaskaulasweb@zohomail.com"]), flush=True)
            print('subject: ' + str(app.config['FLASKY_MAIL_SUBJECT_PREFIX']), flush=True)
            print('text: ' + "Novo usuário cadastrado: " + form.name.data, flush=True)

            if app.config['FLASKY_ADMIN']:
                print('Enviando mensagem...', flush=True)
                send_simple_message([app.config['FLASKY_ADMIN'], "flaskaulasweb@zohomail.com"], 'Novo usuário', form.name.data)
                print('Mensagem enviada...', flush=True)
        else:
            session['known'] = True
        session['name'] = form.name.data
        return redirect(url_for('index'))
    return render_template('index.html', form=form, name=session.get('name'),
                           known=session.get('known', False), users=users)
