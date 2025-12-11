import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import smtplib
from email.message import EmailMessage
from sqlalchemy import or_, and_

load_dotenv()

app = Flask(__name__)
app.jinja_env.globals['os'] = os
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'cambiame')
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nannyclub.db")
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
with app.app_context():
    db.create_all()
    print("Tablas creadas correctamente")


login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    phone = db.Column(db.String(50))
    location = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start = db.Column(db.DateTime, nullable=False)
    end = db.Column(db.DateTime, nullable=False)
    neuro = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='bookings')

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Send email
def send_email_to_nanny(subject, body):
    smtp_host = os.getenv('MAIL_SMTP_HOST')
    smtp_port = int(os.getenv('MAIL_SMTP_PORT', '587'))
    username = os.getenv('MAIL_USERNAME')
    password = os.getenv('MAIL_PASSWORD')
    nanny_email = os.getenv('NANNY_EMAIL')
    use_tls = os.getenv('MAIL_USE_TLS', 'True') == 'True'

    if not (smtp_host and username and password and nanny_email):
        print("Faltan datos SMTP")
        return False

    msg = EmailMessage()
    msg['From'] = username
    msg['To'] = nanny_email
    msg['Subject'] = subject
    msg.set_content(body)

    try:
        #print("DEBUG SMTP HOST:", smtp_host)
        #print("DEBUG SMTP PORT:", smtp_port)
        #print("DEBUG USERNAME:", username)
        #print("DEBUG PASSWORD LENGTH:", len(password) if password else "NO PASSWORD")
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if use_tls:
                server.starttls()
            server.login(username, password)
            server.send_message(msg)
        print("Correo enviado correctamente")
        return True
    except smtplib.SMTPAuthenticationError:
        print("Error de autenticación: revisa tu usuario y contraseña de aplicación")
        return False
    except Exception as e:
        print("Error enviando correo:", e)
        return False



# Routes
@app.route('/')
def index():
    return render_template(
        'index.html',
        nanny_whatsapp=os.getenv('NANNY_WHATSAPP', ''),
        nanny_instagram=os.getenv('NANNY_INSTAGRAM', '#'),
        current_user_email=current_user.email if current_user.is_authenticated else ''
    )


@app.route('/events')
def events():
    current_email = current_user.email if current_user.is_authenticated else ''
    bookings = Booking.query.all()
    events = []
    for b in bookings:
        events.append({
            'id': b.id,
            'title': 'Reservado',
            'start': b.start.isoformat(),
            'end': b.end.isoformat(),
            'allDay': False,
            'extendedProps': {
                'user_email': b.user.email,
                'phone': b.user.phone or '',
                'is_current_user': b.user.email == current_email
            }
        })
    return jsonify(events)

@app.route('/delete_booking/<int:booking_id>', methods=['POST'])
@login_required
def delete_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    # Solo puede borrar su propia reserva
    if booking.user_id != current_user.id:
        return jsonify({'ok': False, 'message': 'No autorizado'}), 403
    
    db.session.delete(booking)
    db.session.commit()
    return jsonify({'ok': True, 'message': 'Reserva eliminada'})
@app.route('/cancel/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        return jsonify({'ok': False, 'message': 'No puedes eliminar esta reserva.'}), 403
    db.session.delete(booking)
    db.session.commit()
    return jsonify({'ok': True, 'message': 'Reserva eliminada.'})




@app.route('/book', methods=['POST'])
@login_required
def book():
    data = request.json or request.form
    try:
        start_dt = datetime.fromisoformat(f"{data.get('start_date')}T{data.get('start_time')}")
        end_dt = datetime.fromisoformat(f"{data.get('end_date')}T{data.get('end_time')}")
        neuro = data.get('neuro', 'Ninguno')
        if end_dt <= start_dt:
            return jsonify({'ok': False, 'message': 'La hora de fin debe ser posterior a la de inicio.'}), 400

        overlapped = Booking.query.filter(
            or_(
                and_(Booking.start <= start_dt, Booking.end > start_dt),
                and_(Booking.start < end_dt, Booking.end >= end_dt),
                and_(Booking.start >= start_dt, Booking.end <= end_dt)
            )
        ).first()
        if overlapped:
            return jsonify({'ok': False, 'message': 'Horario ya ocupado.'}), 400

        booking = Booking(user_id=current_user.id, start=start_dt, end=end_dt, neuro=neuro)
        db.session.add(booking)
        db.session.commit()

        # Correo a la niñera
        subject = f"Nuevo interés de reserva por {current_user.email}"
        whatsapp_number = os.getenv('NANNY_WHATSAPP', '')
        body = f"""
Hola Nancy,

Nuevo usuario interesado:
- Usuario: {current_user.email}
- Teléfono: {current_user.phone or 'No proporcionado'}
- Inicio: {start_dt.strftime('%Y-%m-%d %H:%M')}
- Fin: {end_dt.strftime('%Y-%m-%d %H:%M')}
- Neurodivergencia: {neuro}

Puedes contactar al usuario por WhatsApp: https://wa.me/{current_user.phone if current_user.phone else whatsapp_number}
"""
        send_email_to_nanny(subject, body)

        return jsonify({'ok': True, 'message': 'Reserva realizada y correo enviado.'})
    except Exception as e:
        return jsonify({'ok': False, 'message': f'Error: {e}'}), 500

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        phone = request.form.get('phone')
        location = request.form.get('location')
        if password != confirm:
            flash('Contraseñas no coinciden', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Correo ya registrado', 'danger')
            return redirect(url_for('register'))
        user = User(email=email, phone=phone, location=location)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registro exitoso. Inicia sesión.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email').strip().lower()
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash('Correo o contraseña inválidos', 'danger')
            return redirect(url_for('login'))
        login_user(user)
        flash('Bienvenido.', 'success')
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
