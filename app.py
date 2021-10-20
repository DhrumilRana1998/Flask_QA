from flask import Flask,request,render_template,session,redirect,url_for,flash
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, send, emit, ConnectionRefusedError, join_room
import pickle
import eventlet
import bcrypt
import urllib.request
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
socketio = SocketIO(app, engineio_logger=True, cors_allowed_origins="*")

ENV = 'prod'
select_database = 'almin'

#this is for localhost
if ENV == 'dev':
    app.debug = True
    if select_database == 'dhrumil':
        app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Dhrumil1998@@@localhost/gameApp'
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:almin123@localhost/flaskwebsite490'
# this one is for the heruko
else:
    app.debug = False
    if select_database == 'dhrumil':
        app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://wkmpqniejsynrs:cb8e4d066de141ba34aec6df0e1bc47e2d5741383d1e541a9ffb4d9a230c347a@ec2-18-209-143-227.compute-1.amazonaws.com:5432/d52kv5vd4tka5f'
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://onagbacopzfapd:985b15068892b63537c9a10a74d74d6579c45f677b4cba87594a09806e78e14d@ec2-52-23-87-65.compute-1.amazonaws.com:5432/d29sd9q7h5fs67'

#this is general
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key='very secret key'
db = SQLAlchemy(app)

#this is saving post detail
UPLOAD_FOLDER = 'static/upload/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class accounts(db.Model):
    __tablename__ = 'accounts'
    userID = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.VARCHAR(), unique=True)
    password = db.Column(db.VARCHAR(), unique=False)
    role = db.Column(db.CHAR(1))

    def __init__(self, username, password, role):
        self.username = username
        self.password = password
        self.role = role


class posts(db.Model):
    __tablename__ = 'posts'
    postID = db.Column(db.Integer, primary_key=True)
    uID = db.Column(db.Integer, db.ForeignKey('accounts.userID'), nullable=False)
    image = db.Column(db.Text, nullable=True)
    description = db.Column(db.VARCHAR, nullable=True)
    filename = db.Column(db.Text, nullable=True)
    mimetype = db.Column(db.Text, nullable=True)
    blocked = db.Column(db.Text, nullable=False)

    def __init__(self,uID, image, description, filename, mimetype, blocked):
        self.uID = uID
        self.image = image
        self.description = description
        self.filename = filename
        self.mimetype = mimetype
        self.blocked = blocked


class comments(db.Model):
    __tablename__ = 'comments'
    commentID = db.Column(db.Integer, primary_key=True)
    commenterID = db.Column(db.Integer, db.ForeignKey('accounts.userID'), nullable=False)
    textComment = db.Column(db.VARCHAR(), nullable=False)
    postID = db.Column(db.Integer, db.ForeignKey(posts.postID), nullable=False)

    def __init__(self, commenterID, textComment, postID):
        self.commenterID = commenterID
        self.textComment = textComment
        self.postID = postID

class friends(db.Model):
    __tablename__ = 'friends'
    Number = db.Column(db.Integer, primary_key=True)
    userID = db.Column(db.Integer)
    friendID = db.Column(db.Integer, db.ForeignKey('accounts.userID'), nullable=False)

    def __init__(self, userID, friendID):
        self.userID = userID
        self.friendID = friendID

class message(db.Model):
    __tablename__ = 'message'
    msgID = db.Column(db.Integer, primary_key=True)
    senderID = db.Column(db.Integer, nullable=False)
    receiverID = db.Column(db.Integer, nullable=False)
    msg = db.Column(db.VARCHAR, nullable=False)

    def __init__(self, senderID, receiverID, msg):
        self.senderID = senderID
        self.receiverID = receiverID
        self.msg = msg

@app.route('/')
def entry():
    return render_template("login.html")


@app.route('/login',methods=['POST', 'GET'])
def login():
    nameIN = request.form['username']
    passwordIN = request.form['password'].encode('utf-8')

    # check if username is in the accounts database
    user = accounts.query.filter_by(username=nameIN).first()
    if user:
        # compare password given to database hash
        if bcrypt.checkpw(passwordIN, user.password.encode('utf-8')):
            if user.role == 'U':
                session['name']=request.form['username']
                session['userlevel']="user"
                return redirect(url_for('home'))
            else:
                session['name']=request.form['username']
                session['userlevel'] = 'admin'
                return redirect(url_for('home'))
        else:
            return render_template('login.html', info='Password incorrect.')
    else:
        return render_template('login.html', info='Account with that username does not exist.')


@app.route('/home', methods=['POST', 'GET'])
def home():
    if request.method == 'GET':
        post = posts.query.all()
        commentlist = comments.query.all()
        user = accounts.query.all()

        return render_template('home.html',name=session.get('name'), userlevel=session.get('userlevel'), posts=post, comments=commentlist,users=user)
    if request.method =='POST':
        post = posts.query.all()
        commentlist = comments.query.all()
        user = accounts.query.all()
        userID = db.session.query(accounts.userID).filter_by(username=session.get('name')).first()
        commenttext=request.form['comment_input']
        postID=request.form['postID']
        commentSEND = comments(textComment=commenttext, commenterID=userID, postID=postID)
        db.session.add(commentSEND)
        db.session.commit()
        return redirect('home')
# return a list of post and gian has to make a css file such that it will show in sequence


@app.route('/Friends', methods=['POST', 'GET'])
def friend():
    #getting userid then getting friends and filling friendlist
    user= db.session.query(accounts.userID).filter_by(username=session.get('name')).first()
    friendIDlist=db.session.query(friends.friendID).filter_by(userID=user)
    friendlist = []
    for friendID in friendIDlist:
        f = db.session.query(accounts.username).filter_by(userID=friendID).first()
        friendlist.append(f)
    # getting userid then getting friends and filling friendlist
    print(friendlist)
    return render_template("friends.html",friends=friendlist, title="Friends", name=session.get('name'), userlevel=session.get('userlevel') )
#return a list of all the friends


@app.route('/messanger/<name>/<friendname>', methods=['GET'])
def messanger(name, friendname):
    msgToSend = ''
    sender = session.get('name')
    friendsID = db.session.query(accounts.userID).filter_by(username=friendname).first()  #receiver
    usersID = db.session.query(accounts.userID).filter_by(username=session.get('name')).first() #sender or current user
    sentmsgs = db.session.query(message.msgID,message.msg,message.senderID).filter_by(senderID=usersID,receiverID=friendsID).all() #msgs sent by the current user to friend
    receivedmsgs = db.session.query(message.msgID,message.msg,message.senderID).filter_by(senderID=friendsID,receiverID=usersID).all() #msgs sent by friend to current user
    allmsgs = sentmsgs + receivedmsgs
    allmsgs.sort()
    print(allmsgs)

    if request.method == 'GET':
        return render_template("messanger.html", title="Messanger", msgsALL=allmsgs, msgsSent=sentmsgs, msgsReceived=receivedmsgs, sendersID=usersID[0], friend=friendname, friendID=friendsID[0], name=session.get('name'), userlevel=session.get('userlevel'))



@app.route('/CreatePost', methods=['POST', 'GET'])
def Post():
    if request.method == 'POST':
        usertext = request.form['usertext']
        image = request.files['img']
        if allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            mimetype = image.mimetype
            blocked = "false"
        else:
            flash('Allowed image types are - png, jpg, jpeg, gif')
            return redirect(request.url)

        account = accounts.query.filter_by(username=session.get('name')).first()
        userid = account.userID
        post = posts(uID=userid,image=image.read(), description=usertext, filename=filename, mimetype=mimetype, blocked=blocked)
        db.session.add(post)
        db.session.commit()
        return render_template("createpost.html", title="Home", name=session.get('name'), userlevel=session.get('userlevel'), filename=filename )
    if request.method == 'GET':
        return render_template("createpost.html", title="Create Post", name=session.get('name'), userlevel=session.get('userlevel'))

# gian will add the post through a form post and we will take it and add it to our database
@app.route('/AddAccount', methods=['POST', 'GET'])
def addaccount():
    if request.method == 'POST':
        newuserName = request.form['username']
        passIN = request.form['password']
        newrole = request.form['role']
        newpassword = bcrypt.hashpw(passIN.encode('utf-8'), bcrypt.gensalt())
        user = accounts(username= newuserName, password=newpassword.decode('utf-8'), role=newrole)
        db.session.add(user)
        db.session.commit()
        return render_template("addaccount.html", title="Add Account", name=session.get('name'),userlevel=session.get('userlevel'))

    if request.method == 'GET':
        return render_template("addaccount.html", title="Add Account", name=session.get('name'),userlevel=session.get('userlevel'))

#socketio events
@socketio.on("joined")
def handle_event_joined(data):
    #new room is a room which the user joins when they select a friend to receive messages from and send to
    newRoom = data['userID'] +":" + data['friendID']  #the room is only for this user, not the friend
    print(newRoom)
    join_room(newRoom)
    print(data)

@socketio.on("sendMessage")
def handle_sendMessage_event(data):

    #adding message to the database
    messageSEND = message(msg=data['message'], senderID=data['userID'], receiverID=data['friendID'])
    db.session.add(messageSEND)
    db.session.commit()

    #sending message to the friends receiving room for our user
    sendToRoom = data['friendID'] + ":" + data['userID']
    socketio.emit('receiveMessage',data,room=sendToRoom)
    print("sending to: "+sendToRoom)
    print(data)

# we still need to do block post and create user accounts
if __name__ == '__main__':
    socketio.run(app, debug=True)