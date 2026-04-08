# ============================
# File: app.py
# ============================
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify , request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from flask import send_from_directory
#import json
from openai import OpenAI
from dotenv import load_dotenv
import google.generativeai as genai

# Load videos from JSON



# ============================
# Flask app setup
# ============================




BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-key"),
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(BASE_DIR, 'edutube.db')}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,

    
)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ============================
# Models
# ============================
subscriptions = db.Table(
    "subscriptions",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id")),
    db.Column("channel_id", db.Integer, db.ForeignKey("channel.id")),
)

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads/videos')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER



class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    profile_pic = db.Column(db.String(300))
    channels = db.relationship("Channel", backref="owner", lazy=True)
    likes = db.relationship("Like", backref="user", lazy=True)
    comments = db.relationship("Comment", backref="user", lazy=True)
    
    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

class Channel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    bio = db.Column(db.Text, default="")
    owner_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subscribers = db.relationship("User", secondary=subscriptions, backref="subscriptions")
    videos = db.relationship("Video", backref="channel", lazy=True)

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    category = db.Column(db.String(50), default="Programming")
    tags = db.Column(db.String(250), default="")  # comma separated
    duration_sec = db.Column(db.Integer, default=0)
    views = db.Column(db.Integer, default=0)
    url = db.Column(db.String(500), nullable=False)
   # thumb_url = db.Column(db.String(500), default="https://images.unsplash.com/photo-1518773553398-650c184e0bb3?q=80&w=1200&auto=format&fit=crop")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    channel_id = db.Column(db.Integer, db.ForeignKey("channel.id"), nullable=False)

    likes = db.relationship("Like", backref="video", lazy=True, cascade="all, delete-orphan")
    comments = db.relationship("Comment", backref="video", lazy=True, cascade="all, delete-orphan")

class Like(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey("video.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    video_id = db.Column(db.Integer, db.ForeignKey("video.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    questions = db.relationship('Question', backref='quiz', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    options = db.relationship('Option', backref='question', lazy=True)

class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    option_text = db.Column(db.String(200), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
class UserQuizResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)  # agar Flask-Login use ho raha hai to current_user.id
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)  # total questions
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)



# -----------------------
# Flask app setup
# -----------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-key"),
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(BASE_DIR, 'edutube.db')}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    UPLOAD_FOLDER=os.path.join(BASE_DIR, 'uploads')
)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)



# -----------------------
# Database setup
# -----------------------


class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    message = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=db.func.current_timestamp())

# Create tables
with app.app_context():
    db.create_all()

#features route landing page ---------------------------
@app.route("/")
def landing():
    return render_template("features.html")
# ---------------------------------------


# Routes
# -----------------------
@app.route("/feedback-form")
def feedback_form():
    return render_template("feedback.html")  # your HTML form



@app.route("/feedback-list", methods=["GET"])
def feedback_list():
    feedbacks = Feedback.query.order_by(Feedback.date.desc()).all()
    output = []
    for fb in feedbacks:
        output.append({
            "id": fb.id,
            "name": fb.name,
            "email": fb.email,
            "rating": fb.rating,
            "message": fb.message,
            "date": fb.date.strftime("%Y-%m-%d %H:%M:%S")
        })
    return jsonify(output)

# -----------------------
# Run app
# -----------------------




# ======= Models =======
class UserScore(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    score = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<User {self.username}: {self.score}>'

# ======= Helper functions =======
def update_score(username, points):
    user = UserScore.query.filter_by(username=username).first()
    if user:
        user.score += points
    else:
        user = UserScore(username=username, score=points)
        db.session.add(user)
    db.session.commit()

# ======= CLI =======


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
def get_leaderboard(top_n=10):
    # Aggregate total score per user from quiz results
    results = db.session.query(
        User.id.label('user_id'),
        User.name.label('username'),
        db.func.sum(UserQuizResult.score).label('score')
    ).join(UserQuizResult, User.id == UserQuizResult.user_id)\
     .group_by(User.id)\
     .order_by(db.desc('score'))\
     .limit(top_n).all()
    
    return results



# ============================
# Helpers
# ============================
CATEGORIES = ["All", "Programming", "Data Science", "Design", "Business", "AI/ML", "Web Dev", "Mobile", "Personal Dev"]


# Routes
@app.route("/home", endpoint="index")
def home():
    q = request.args.get("q", "").strip().lower()
    cat = request.args.get("category", "All")

    # Videos filter
    base = Video.query
    if cat and cat != "All":
        base = base.filter_by(category=cat)
    if q:
        like = f"%{q}%"
        base = base.filter(db.or_(Video.title.ilike(like), Video.description.ilike(like), Video.tags.ilike(like)))
    videos = base.order_by(Video.created_at.desc()).all()

    # Leaderboard
    top_users = get_leaderboard()

    # ⭐ ADD THIS ⭐
    quizzes = Quiz.query.all()

    return render_template(
        "index.html",
        videos=videos,
        categories=CATEGORIES,
        current_cat=cat,
        q=q,
        users=top_users,
        quizzes=quizzes   # ⭐ pass quizzes to HTML
    )


@app.cli.command("init-db")
def init_db():
    db.create_all()
    print("✅ Database initialized!")
    
@app.cli.command("seed")
def seed():
    """Seed the database with some videos"""
    from datetime import datetime

    sample_videos = [
        {
            "title": "Python Full Course for Beginners",
            "url": "https://www.youtube.com/embed/t2_Q2BRzeEE?si=_e6sx7YrPEWT3YhF",
            "topic": "Python"
        },
        {
            "title": "JavaScript Tutorial for Beginners",
            "url": "https://www.youtube.com/embed/VlPiVmYuoqw?si=o6FtAsTRhbkKvvCl",
            "topic": "JavaScript"
        },
        {
            "title": "HTML & CSS Crash Course",
            "url": "https://www.youtube.com/embed/HBqWsrqK89U?si=m6vk1RRyXe8aA4Gk",
            "topic": "Web Development"
        },
        {
            "title": "React JS Crash Course",
            "url": "https://www.youtube.com/embed/RGKi6LSPDLU?si=M92L_DAmUwKpFBiP",
            "topic": "React"
        },
        {
            "title": "Machine Learning Full Course",
            "url": "https://www.youtube.com/embed/ie4oGI85SAE?si=CoyL0tREWOaEkGHi",
            "topic": "Machine Learning"
        },
         {
        "title": "Python Tutorial for Beginners",
        "url": "https://www.youtube.com/embed/UrsmFxEIp5k?si=mlBsBZbwff9fSYz2",
        "topic": "Python"
    },
    {
        "title": "Flask Crash Course",
        "url": "https://www.youtube.com/embed/oA8brF3w5XQ?si=0AWHoVRIJIl_4edO",
        "topic": "Flask"
    },
    {
        "title": "Flask Crash Course",
        "url": "https://www.youtube.com/embed/oA8brF3w5XQ?si=0AWHoVRIJIl_4edO",
        "topic": "Flask"
    },
    {
        "title": "C++ Programming",
        "url": "https://www.youtube.com/embed/bL-o2xBENY0?si=RJuEbBD7WtLUiKCO",
        "topic": "Flask"
    }
    
    ]

    if Channel.query.count() == 0:
        from app import User
        # Assume user_id 1 exists, otherwise change accordingly
        c = Channel(name="Demo Channel", owner_id=1)
        db.session.add(c)
        db.session.commit()
        print("✅ Demo channel created!")

    if Video.query.count() == 0:  # sirf agar DB empty ho
        channel_id = Channel.query.first().id
        for vid in sample_videos:
            video = Video(
                title=vid["title"],
                url=vid["url"],
                category=vid["topic"],
                channel_id=channel_id,
                upload_date=datetime.utcnow()
            )
            db.session.add(video)
        db.session.commit()
        print("✅ Sample videos added!")
    else:
        print("DB already has videos, nothing added.")






load_dotenv()  # .env file load kare

genai.configure(api_key=os.getenv("YOUR_API_KEY_HERE"))  # API key ka name string me

@app.route("/search")
def search():
    query = request.args.get("q", "")
    if query:
        videos = Video.query.filter(Video.title.ilike(f"%{query}%")).all()
    else:
        videos = Video.query.all()
    return render_template("search.html", videos=videos)

from flask_login import login_required

@app.route('/quiz/<int:quiz_id>', methods=['GET', 'POST'])
@login_required  # Add this!
def take_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).all()

    if request.method == 'POST':
        score = 0
        for q in questions:
            selected = request.form.get(str(q.id))
            correct_option = Option.query.filter_by(question_id=q.id, is_correct=True).first()
            if selected and correct_option and int(selected) == correct_option.id:
                score += 1

        result = UserQuizResult(
            user_id=current_user.id, 
            quiz_id=quiz_id, 
            score=score,
            total=len(questions)
        )
        db.session.add(result)
        db.session.commit()
        flash(f'You scored {score} out of {len(questions)}!', 'success')
        return redirect(url_for('quiz_results'))

    return render_template('quiz.html', quiz=quiz, questions=questions)

@app.route('/quiz_results')
def quiz_results():
    results = UserQuizResult.query.filter_by(user_id=current_user.id).all()
    return render_template('quiz_results.html', results=results)





@app.route('/dashboard')
@login_required
def dashboard():
    videos = Video.query.order_by(Video.created_at.desc()).all()
    # safe channel selection
    channel = current_user.channels[0] if current_user.channels else None
    return render_template('dashboard.html', videos=videos, current_user=current_user, channel=channel)

@app.route('/delete/<int:video_id>', methods=['POST'])
def delete_video(video_id):
    video = Video.query.get_or_404(video_id)
    db.session.delete(video)
    db.session.commit()
    flash(f"Video '{video.title}' deleted successfully!", "success")
    return redirect(url_for('dashboard'))





@app.route("/profile/upload_photo", methods=["GET", "POST"])
@login_required
def upload_profile_photo():
    if request.method == "POST":
        file = request.files.get("photo")
        if not file:
            flash("No file selected", "warning")
            return redirect(url_for("dashboard"))

        filename = secure_filename(file.filename)
        upload_folder = os.path.join("uploads", "profiles", str(current_user.id))
        os.makedirs(upload_folder, exist_ok=True)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        # Save path in DB
        current_user.profile_pic = f"/uploads/profiles/{current_user.id}/{filename}"
        db.session.commit()
        flash("Profile photo updated!", "success")
        return redirect(url_for("dashboard"))

    return redirect(url_for("dashboard"))

#@app.route('/uploads/profiles/<int:user_id>/<path:filename>')
##def uploaded_profile_photos(user_id, filename):

@app.route("/videos")
def show_videos():
    videos = Video.query.all()
    liked_map = {}
    if current_user.is_authenticated:
        for v in videos:
            liked_map[v.id] = Like.query.filter_by(user_id=current_user.id, video_id=v.id).first() is not None
    return render_template("video.html", videos=videos, liked_map=liked_map)

@app.route("/video/<int:vid>")
def video_detail(vid):
    v = Video.query.get_or_404(vid)
    v.views += 1
    db.session.commit()
    
    user_liked = False
    if current_user.is_authenticated:
        user_liked = Like.query.filter_by(user_id=current_user.id, video_id=v.id).first() is not None

    quiz_available = hasattr(v, 'quiz_id') and v.quiz_id is not None

    return render_template("video.html", v=v, user_liked=user_liked, quiz_available=quiz_available)


@app.route("/like/<int:vid>", methods=["POST"])
@login_required
def like_video(vid):
    v = Video.query.get_or_404(vid)
    existing = Like.query.filter_by(user_id=current_user.id, video_id=v.id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        liked = False
    else:
        like = Like(user=current_user, video=v)
        db.session.add(like)
        db.session.commit()
        liked = True
    return jsonify({"liked": liked, "count": len(v.likes)})

@app.route("/comment/<int:vid>", methods=["POST"])
@login_required
def add_comment(vid):
    v = Video.query.get_or_404(vid)
    text = (request.form.get("body") or "").strip()
    if not text:
        flash("Comment cannot be empty", "warning")
        return redirect(url_for("video_detail", vid=vid))
    c = Comment(body=text, user=current_user, video=v)
    db.session.add(c)
    db.session.commit()
    return redirect(url_for("video_detail", vid=vid) + "#comments" )

#UPLOAD_FOLDER = 'uploads/videos'
@app.route('/upload', methods=['GET','POST'])
@login_required
def upload():
    if request.method == 'POST':
        title = request.form['title']
        category = request.form['category']
        youtube_url = request.form.get('youtube_url', '').strip()
        file = request.files.get('video_file')

        if youtube_url:
            video_url = youtube_url
        elif file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            video_url = f"/uploads/{filename}"
        else:
            flash("Provide YouTube link or upload a video.", "danger")
            return redirect(url_for('upload'))

        # Set channel_id properly
        channel_id = current_user.channels[0].id if current_user.channels else 1

        try:
            new_video = Video(
                title=title,
                url=video_url,
                category=category,
                channel_id=channel_id
            )
            db.session.add(new_video)
            db.session.commit()
            flash("Video uploaded successfully!", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error uploading video: {e}", "danger")
            print("DB Error:", e)
            return redirect(url_for('upload'))

        return redirect(url_for('dashboard'))

    return render_template('upload.html')





print(app.config['UPLOAD_FOLDER'])
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route("/channel/<int:cid>/subscribe", methods=["POST"])
@login_required
def subscribe(cid):
    ch = Channel.query.get_or_404(cid)
    if current_user in ch.subscribers:
        ch.subscribers.remove(current_user)
        db.session.commit()
        return jsonify({"subscribed": False, "count": len(ch.subscribers)})
    ch.subscribers.append(current_user)
    db.session.commit()
    return jsonify({"subscribed": True, "count": len(ch.subscribers)})




quiz_data = [
    {
        "question": "What is the capital of India?",
        "options": ["Mumbai", "Delhi", "Kolkata", "Chennai"],
        "answer": "Delhi"
    },
    {
        "question": "Which language is used for web apps?",
        "options": ["Python", "JavaScript", "C++", "Java"],
        "answer": "JavaScript"
    }
    ,
    {
        "question": "Which language is used for style?",
        "options": ["Python", "JavaScript", "CSS", "Java"],
        "answer": "CSS"
    }
    ,
    {
        "question": "Which Programming language is used to write  web page?",
        "options": ["Python", "C", "html", "Java"],
        "answer": "html"
    }
    ,
    {
        "question": "Which is the program  used for painting etc.?",
        "options": ["Fine Arts", "B.Tech", "Pharmacy", "Nursing"],
        "answer": "Fine Arts"
    }
    ,
    {
        "question": "Which Course is used for Enginnering?",
        "options": ["Nursing", "B.Tech", "BBA", "Pharmacy"],
        "answer": "B.Tech"
    }
    ,
    {
        "question": "Who is inventing the bulb ?",
        "options": ["Thomas Alva Edition", "Newton", "Python", "William Shakspeare"],
        "answer": "Thomas Alva Edition"
    }
    ,
    {
        "question": "Which is the flag of india ?",
        "options": ["Tiranga", "japanese", "Ganga", "Jammu & Kashmir "],
        "answer": "Tiranga"
    }
    ,
    {
        "question": "In following  languages which language is  used for DSA ?",
        "options": ["Html", "CSS", "C++", "HTML3"],
        "answer": "C++"
    }
    ,
    {
        "question": "Which language is used for web apps?",
        "options": ["Python", "JavaScript", "C++", "Java"],
        "answer": "JavaScript"
    }
    ,
    {
        "question": "Which language is used for web apps?",
        "options": ["Python", "JavaScript", "C++", "Java"],
        "answer": "JavaScript"
    }
]

@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if request.method == "POST":
        score = 0
        for i, q in enumerate(quiz_data):
            user_answer = request.form.get(f"question-{i}")
            if user_answer == q["answer"]:
                score += 1
        return f"Your score: {score}/{len(quiz_data)} ✅"
    
    return render_template("quiz.html", quiz=quiz_data)




# -----------------------

# Page to show all quizzes
@app.route("/all_quizzes")
@login_required
def all_quizzes():
    quizzes = Quiz.query.all()
    return render_template("all_quizzes.html", quizzes=quizzes)



    

@app.route('/create_quiz', methods=['GET', 'POST'])
@login_required
def create_quiz():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description')

        quiz = Quiz(title=title, description=description)
        db.session.add(quiz)
        db.session.commit()

        return redirect(f'/add_question/{quiz.id}')

    return render_template('create_quiz.html')


@app.route('/add_question/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def add_question(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    if request.method == 'POST':
        q_text = request.form['question_text']
        correct_option = request.form['correct_option']

        question = Question(quiz_id=quiz.id, question_text=q_text)
        db.session.add(question)
        db.session.commit()

        # Save options
        for i in range(1, 5):
            opt_text = request.form[f'option{i}']
            is_correct = (correct_option == f'option{i}')

            option = Option(
                question_id=question.id,
                option_text=opt_text,
                is_correct=is_correct
            )
            db.session.add(option)

        db.session.commit()

        if 'finish' in request.form:
            flash("Quiz Created Successfully!", "success")
            return redirect(url_for('index'))

        return redirect(url_for('add_question', quiz_id=quiz.id))

    return render_template('add_question.html', quiz=quiz)


@app.route('/attempt_quiz/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def attempt_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = Question.query.filter_by(quiz_id=quiz_id).all()

    if request.method == 'POST':
        score = 0
        total = len(questions)

        for q in questions:
            selected_option_id = request.form.get(str(q.id))
            if selected_option_id:
                selected_option = Option.query.get(int(selected_option_id))
                if selected_option.is_correct:
                    score += 1

        # ✅ current_user.id use karo
        result = UserQuizResult(
            user_id=current_user.id,
            quiz_id=quiz_id,
            score=score,
            total=total
        )
        db.session.add(result)
        db.session.commit()

        return redirect(f'/leaderboard/{quiz_id}')

    return render_template('attempt_quiz.html', quiz=quiz, questions=questions)

@app.route('/leaderboard/<int:quiz_id>')
def leaderboard(quiz_id):
    results = db.session.query(
        UserQuizResult,
        User
    ).join(User, UserQuizResult.user_id == User.id) \
     .filter(UserQuizResult.quiz_id == quiz_id) \
     .order_by(UserQuizResult.score.desc()) \
     .all()

    return render_template('leaderboard.html', results=results)



# -------- Auth --------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        pw = request.form.get("password","")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(pw):
            login_user(user)
            flash("Welcome back!", "success")
            return redirect(url_for("index"))
        flash("Invalid credentials", "danger")
    return render_template("auth_login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name"," ").strip()
        email = request.form.get("email"," ").strip().lower()
        pw = request.form.get("password"," ")
        if not name or not email or not pw:
            flash("All fields are required", "danger")
            return redirect(url_for("register"))
        if User.query.filter_by(email=email).first():
            flash("Email already registered", "warning")
            return redirect(url_for("register"))
        u = User(name=name, email=email)
        u.set_password(pw)
        db.session.add(u)
        db.session.commit()
        flash("Account created. Please sign in.", "success")
        return redirect(url_for("login"))
    return render_template("auth_register.html")



@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Signed out", "info")
    return redirect(url_for("index"))

# ============================
# CLI & Init
# ============================
@app.cli.command("init-db")
def init_db():
    db.create_all()
    seed_if_empty()
    print("Database initialized and demo data added.")


##with open("videos.json", "r", encoding="utf-8") as f:
  #  videos_data = json.load(f)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        #seed()
        #seed_leaderboard()

    print("SERVER STARTING...")
    app.run(debug=True)


