import os
from flask import (
    Flask, render_template, redirect, url_for, request, flash
)
from flask_login import (
    login_user, logout_user, login_required, current_user
)
from werkzeug.utils import secure_filename

from config import Config
from extensions import db, login_manager
from models import User, Analysis
from analyzer.pdf_utils import extract_text_from_pdf
from analyzer.matcher import compute_match, find_missing_skills


def allowed_file(filename, allowed):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    with app.app_context():
        db.create_all()

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form["username"].strip()
            email = request.form["email"].strip()
            password = request.form["password"]

            if User.query.filter_by(username=username).first():
                flash("Username already taken.", "danger")
            elif User.query.filter_by(email=email).first():
                flash("Email already registered.", "danger")
            else:
                user = User(username=username, email=email)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                flash("Account created. Please log in.", "success")
                return redirect(url_for("login"))
        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form["username"].strip()
            password = request.form["password"]

            print("Username entered:", username)

            user = User.query.filter_by(username=username).first()

            print("User found:", user)

            if user:
                print("Password check:", user.check_password(password))

            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for("dashboard"))

            flash("Invalid credentials.", "danger")

        return render_template("login.html")

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.route("/dashboard", methods=["GET", "POST"])
    @login_required
    def dashboard():
        if request.method == "POST":
            job_description = request.form.get("job_description", "").strip()
            file = request.files.get("resume")

            if not file or file.filename == "":
                flash("Please upload a resume PDF.", "danger")
                return redirect(url_for("dashboard"))
            if not allowed_file(file.filename, app.config["ALLOWED_EXTENSIONS"]):
                flash("Only PDF files are allowed.", "danger")
                return redirect(url_for("dashboard"))
            if not job_description:
                flash("Please paste a job description.", "danger")
                return redirect(url_for("dashboard"))

            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)

            resume_text = extract_text_from_pdf(save_path)
            if not resume_text:
                flash("Could not extract text from the PDF.", "danger")
                return redirect(url_for("dashboard"))

            score = compute_match(resume_text, job_description)
            missing = find_missing_skills(resume_text, job_description)

            analysis = Analysis(
                user_id=current_user.id, filename=filename, match_score=score
            )
            db.session.add(analysis)
            db.session.commit()

            return render_template(
                "result.html", score=score, missing=missing, filename=filename
            )

        history = (
            Analysis.query.filter_by(user_id=current_user.id)
            .order_by(Analysis.created_at.desc())
            .all()
        )
        return render_template("dashboard.html", history=history)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
