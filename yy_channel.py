# -*- coding: utf-8 -*-
import os
import datetime
import hashlib
import flask
import flask.ext.login as login
import werkzeug
from flask.ext.login import login_user, login_required, logout_user, fresh_login_required
from sqlalchemy import create_engine, sql, Column, Integer, String, Boolean
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

SELF_HOME_PATH = os.path.dirname(os.path.abspath(__file__))

app = flask.Flask(__name__)
app.config.update(
    DATABASE_URI = 'sqlite:////'+SELF_HOME_PATH+'/yy_channel.db',
    SECRET_KEY = 'test key',#os.urandom(24),
    UPLOADED_FILES_DIRECTORY = SELF_HOME_PATH+'/uploaded_files/',
    #UPLOADED_FILES_DIRECTORY = os.path.join(SELF_HOME_PATH, '/uploaded_files/'),
    #UPLOADED_MEDIA_FILES_PARENT_URI = '/uploaded_files/',
    UPLOADED_MEDIA_FILES_PARENT_URI = SELF_HOME_PATH+'/uploaded_files/',
    PLAIN_TEXT_EXTENSIONS = ['', '.txt', '.py'],
    HTML_EXTENSIONS = ['.odt'],
    SOUND_EXTENSIONS = [],
    BINARY_EXTENSIONS = ['.zip', '.tar.gz', '.exe'],
    MOVIE_EXTENSIONS = ['.swf', '.flv', '.mp4', '.mov'],
    DEBUG = True
)

engine = create_engine(app.config['DATABASE_URI'], encoding='utf-8')
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    Base.metadata.create_all(bind=engine)

class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True)
    active = Column(Boolean)
    hashed_password = Column(String)
    name = Column(String)

    def __init__(self, id, hashed_password, name, active=True):
        self.id = id
        self.active = active
        self.hashed_password = hashed_password
        self.name = name

    def is_authenticated(self):
        return True

    def is_active(self):
        return self.active

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    def get_hashed_password(self):
        return self.hashed_password

    def get_name(self):
        return self.name
    """
    def get_auth_token(self):
        #return login.make_secure_token(self.name)
        return u'1'
    """

login_manager = login.LoginManager()
login_manager.login_view == 'login'
login_manager.login_message == 'Please log in'
login_manager.session_protection = "strong"
login_manager.setup_app(app)


@login_manager.user_loader
def load_user(id):
    return User.query.filter_by(id=id).first()

"""
@login_manager.token_loader
def load_token(token):
    return USERS.get(int(token))
"""

@login_manager.unauthorized_handler
def unauthorized():
    return flask.redirect(flask.url_for('login'))


class File(Base):
    __tablename__ = 'files'
    id = Column(String, primary_key=True)
    name = Column(String)
    extension = Column(String)
    uploader_id = Column(String)
    uploader_comment = Column(String)
    upload_date = Column(String)
    image_id = Column(String)
    view_count = Column(Integer)


    def __str__(self):
        return '{{File: {id}, {name}, {ext}, {uid}}}'.format(id=self.id, name=self.name, ext=self.extension, uid=self.uploader_id)

    def __init__(self, id, name, extension, uploader_id, uploader_comment, image_id):
        self.id = id
        self.name = name
        self.extension = extension.lower()
        self.uploader_id = uploader_id
        self.uploader_comment = uploader_comment
        self.upload_date = datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S")
        self.image_id = image_id
        self.view_count = 0

    def get_id(self):
        return self.id

    def get_name(self):
        return self.name

    def get_extension(self):
        return self.extension

    def get_uploader_id(self):
        return self.uploader_id
    
    def get_uploader_comment(self):
        return self.uploader_comment

    def get_upload_date(self):
        return self.upload_date

    def get_image_id(self):
        return self.image_id

    def get_view_count(self):
        return self.view_count

    def increment_view_count(self):
        self.view_count = self.view_count + 1

class FileTag(Base):
    __tablename__ = 'file_tags'
    text = Column(String, primary_key=True)

    def __str__(self):
        return '{{Tag: {text}}}'.format(text=self.text)

    def __init__(self, text):
        self.text = text

    def get_text(self):
        return self.text

class FileComment(Base):
    __tablename__ = 'file_comments'
    id = Column(String, primary_key=True)
    make_date = Column(String)
    text = Column(String)

    def __init__(self, id, make_date, text):
        self.id = id
        self.make_date = make_date
        self.text = text

    def get_id(self):
        return id

    def get_make_date(self):
        return self.make_date

    def get_text(self):
        return text


@app.route('/')
def slash():
    return flask.redirect(flask.url_for('index'))

@app.route('/index')
@login_required
def index():
    files = File.query.order_by(File.id)
    return flask.render_template('index.html', files=files)

@app.route('/view')
@login_required
def view():
    print "request.args['fileid']:", flask.request.args['fileid']
    fileid = flask.request.args.get('fileid', '')
    if not fileid is '':
        try:
            file = File.query.filter_by(id=fileid).first()
            file.increment_view_count()
            db_session.commit()
            if file.get_extension() in app.config['PLAIN_TEXT_EXTENSIONS']:
                file_path = os.path.join(app.config["UPLOADED_FILES_DIRECTORY"], file.get_id())
                contents = unicode(open(file_path, "r").read(), 'utf_8')
                return flask.render_template('plain_text_view.html', file=file, contents=contents)
            if file.get_extension() in app.config['HTML_EXTENSIONS']:
                file_path = os.path.join(app.config["UPLOADED_FILES_DIRECTORY"], file.get_id())+'.htm'
                if os.path.exists(file_path):
                    contents = unicode(open(file_path, "r").read(), 'utf_8')
                    return flask.render_template('html_view.html', file=file, contents=contents)
                else:
                    flask.flash("HtmlVersion not found.")
                    return flask.redirect(flask.url_for('index'))
            if file.get_extension() in app.config['MOVIE_EXTENSIONS']:
                return flask.render_template('movie_view.html', file=file, 
                    media_file_uri=os.path.join(app.config['UPLOADED_MEDIA_FILES_PARENT_URI'],file.get_id()))
            if file.get_extension() in app.config['BINARY_EXTENSIONS']:
                return flask.render_template('binary_view.html', file=file, 
                    media_file_uri=os.path.join(app.config['UPLOADED_MEDIA_FILES_PARENT_URI'],file.get_id()))
            flask.flash("Invalid file type.")
        except:
            raise
            flask.flash("InvalidFileId")
    return flask.redirect('index')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if flask.request.method == 'POST' and 'email' and 'password' and 'name' in flask.request.form:
        id = flask.request.form['email']
        hashed_password = flask.request.form['password'] # todo
        name = flask.request.form['name']
        db_session.add(User(id, hashed_password, name))
        db_session.commit()
        return flask.redirect(flask.url_for('login'))
    return flask.render_template('register.html')

@app.route('/user', methods=['GET', 'POST'])
@login_required
def user():
    if flask.request.method == 'POST':
        return flask.redirect(flask.url_for('login'))
    user = flask.ext.login.current_user
    return flask.render_template('user.html')

@app.route("/upload", methods=['GET', 'POST'])
@login_required
def upload():
    if flask.request.method == 'POST':
        file_in_request = flask.request.files['file']
        if file_in_request:
            uploader_comment = flask.request.form.get('uploader_comment', u'(no uploader\'s comment)')
            if uploader_comment is u'':
                uploader_comment = u'(no uploader\'s comment)'
            unsafe_origin_filename, fileextension = os.path.splitext(file_in_request.filename)
            filename = flask.request.form.get('title', unsafe_origin_filename)
            if filename is u'':
                filename = unsafe_origin_filename

            uploader_id = flask.ext.login.current_user.get_id()
            content = file_in_request.stream.read().encode('hex')
            fileid = hashlib.md5(uploader_id+'filename+fileextension'+content).hexdigest()
            file = File(fileid, filename, fileextension, flask.ext.login.current_user.get_id(), uploader_comment, 'wirelessia_logo.jpg')
            try:
                same_count = File.query.filter_by(id=file.get_id()).count()
                if same_count is not 0:
                    raise
                    
                db_session.add(file)
                db_session.commit()
                file_in_request.seek(0,0)
                file_in_request.save(os.path.join(app.config["UPLOADED_FILES_DIRECTORY"], fileid))
                if file.get_extension() == '.odt':
                    file_path = os.path.join(app.config['UPLOADED_FILES_DIRECTORY'], file.get_id())
                    os.system('libreoffice --headless --convert-to htm:HTML {odt_file} --outdir {out_dir}'.format(odt_file=file_path, out_dir=app.config['UPLOADED_FILES_DIRECTORY']))

            except:
                raise
                flask.flash("SameIdFileAlreadyExists")
            #return flask.redirect(flask.url_for("upload.html"))
            flask.flash("Uploaded!")
            return flask.render_template("uploaded.html")
    return flask.render_template("upload.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'POST' and 'email' in flask.request.form:
        id = flask.request.form['email']
        password = flask.request.form['password']
        user = User.query.filter_by(id=id).first()
        if not user == None and user.get_hashed_password() == password:
            if login_user(user, remember=True):
                return flask.redirect(flask.request.args.get('next') or flask.url_for('index'))
    return flask.render_template('login.html')

@app.route('/reauth', methods=['GET', 'POST'])
@login_required
def reauth():
    if flask.request.method == 'POST':
        login.confirm_login()
        return flask.redirect(flask.request.args.get('next'))
    return flask.render_template('reauth.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return flask.redirect(flask.url_for('index'))
                
if __name__ == '__main__':
    app.run()
