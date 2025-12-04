import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from dotenv import load_dotenv

load_dotenv("config.env")

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# Base de datos SQLite local
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

# Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Mail
app.config['MAIL_SERVER'] = os.getenv("MAIL_SMTP_HOST")
app.config['MAIL_PORT'] = int(os.getenv("MAIL_SMTP_PORT"))
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_USE_TLS'] = os.getenv("MAIL_USE_TLS") == "True"
app.config['MAIL_USE_SSL'] = False

mail = Mail(app)

# Datos de contacto
NANNY_EMAIL = os.getenv("NANNY_EMAIL")
NANNY_WHATSAPP = os.getenv("NANNY_WHATSAPP")
NANNY_INSTAGRAM = os.getenv("NANNY_INSTAGRAM")

# ------------ MODELO USUARIO ------------

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(200))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------ RUTAS ------------

@app.route("/")
def index():
    return render_template(
        "index.html",
        nanny_email=NANNY_EMAIL,
        nanny_whatsapp=NANNY_WHATSAPP,
        nanny_instagram=NANNY_INSTAGRAM
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if User.query.filter_by(email=email).first():
            flash("El correo ya está registrado.")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)
        new_user = User(email=email, password=hashed_password)

        db.session.add(new_user)
        db.session.commit()

        flash("Cuenta creada correctamente.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash("Correo o contraseña incorrectos.")
            return redirect(url_for("login"))

        login_user(user)
        return redirect(url_for("index"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))


# ------------ API: Agendar cita ------------

@app.route("/api/book", methods=["POST"])
@login_required
def api_book():
    data = request.json

    msg = Message(
        subject="Nueva solicitud de cita",
        sender=os.getenv("MAIL_USERNAME"),
        recipients=[NANNY_EMAIL]
    )

    msg.body = f"""
Nueva cita solicitada:

Padre/Madre: {data['parent_name']}
Hijo: {data['child_name']}
Edad: {data['child_age']}
Fecha: {data['date']}
Hora: {data['time']}
Comentarios: {data['comments']}

Solicitado por: {current_user.email}
"""

    mail.send(msg)

    return jsonify({"message": "Cita enviada correctamente."})


# ------------ MAIN ------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
