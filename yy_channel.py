import os
import hashlib
import flask
import flask.ext.login as login
import werkzeug
from flask.ext.login import login_user, login_required, logout_user, fresh_login_required
from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base

app = flask.Flask(__name__)
app.config.update(
    DATABASE_URI = 'sqlite:///yy_channel.db',
    SECRET_KEY = 'test key',#os.urandom(24),
    UPLOADED_FILES_DIRECTORY = './uploaded_files/',
    PLAIN_TEXT_EXTENSIONS = ['.txt'],
    MOVIE_EXTENSIONS = ['.flv'],
    DEBUG = True
)

engine = create_engine(app.config['DATABASE_URI'])
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    Base.metadata.create_all(bind=engine)

class User(Base):
    __tablename__ = 'users'
    id = Column(String, primary_key=True)
    active = Column(Boolean)

    def __init__(self, id, active=True):
        self.id = id
        self.active = active

    def is_authenticated(self):
        return True

    def is_active(self):
        return self.active

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id
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

    def __str__(self):
        return '{{File {id}, {name}, {ext}, {uid}}}'.format(id=self.id, name=self.name, ext=self.extension, uid=self.uploader_id)

    def __init__(self, id, name, extension, uploader_id):
        self.id = id
        self.name = name
        self.extension = extension
        self.uploader_id = uploader_id

    def get_id(self):
        return self.id

    def get_name(self):
        return self.name

    def get_extension(self):
        return self.extension

    def get_uploader_id(self):
        return self.uploader_id

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
            print file
            #print app['PLAIN_TEXT_EXTENSIONS']
            print file.get_extension()
            if file.get_extension() in app.config['PLAIN_TEXT_EXTENSIONS']:
                file_path = os.path.join(app.config["UPLOADED_FILES_DIRECTORY"], file.get_id())
                contents = open(file_path, "r").read()#.replace('\n', '<br />')
                return flask.render_template('plain_text_view.html', file=file, contents=contents)
        except:
            #raise
            flask.flash("InvalidFileId")
            pass
    return flask.redirect('index')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if flask.request.method == 'POST' and 'email' in flask.request.form:
        id = flask.request.form['email']
        db_session.add(User(id))
        db_session.commit()
        return flask.redirect(flask.url_for('login'))
    return flask.render_template('register.html')


@app.route("/upload", methods=['GET', 'POST'])
@login_required
def upload():
    if flask.request.method == 'POST':
        file = flask.request.files['file']
        if file:
            unsafe_filename, fileextension = os.path.splitext(file.filename)
            filename = werkzeug.secure_filename(unsafe_filename)
            uploader_id = flask.ext.login.current_user.get_id()
            fileid = hashlib.md5(uploader_id+filename+fileextension).hexdigest()
            try:
                db_session.add(File(fileid, filename, fileextension, flask.ext.login.current_user.get_id()))
                db_session.commit()
                file.save(os.path.join(app.config["UPLOADED_FILES_DIRECTORY"], fileid))
            except:
                print 'Same id file exists.'
            return flask.render_template("uploaded.html",)
    return flask.render_template("upload.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'POST' and 'email' in flask.request.form:
        id = flask.request.form['email']
        user = User.query.filter_by(id=id).first()
        if not user == None:
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
