from flask import Flask, jsonify, render_template, url_for, flash,abort, redirect, request, abort,send_from_directory, get_flashed_messages,session
import uuid
from flask_socketio import SocketIO, send
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from flask_wtf.csrf import CSRFProtect  
from werkzeug.utils import secure_filename
try:
    from PIL import Image
except Exception:
    Image = None
from models import site, User, File
from config import Config
from markupsafe import Markup, escape
from itertools import groupby
from flask_migrate import Migrate 
from zoneinfo import ZoneInfo
from datetime import timezone
from sqlalchemy import func
from datetime import datetime, timedelta
import pyotp
import qrcode
import io
import base64
import os
import pyclamd
from functools import wraps
try:
    from docx import Document
except Exception as e:
    print(f"Warning: python-docx not loaded: {e}")
    Document = None
from waitress import serve
import sys
import secrets

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'zip',"webp", 'txt',  'css', 'html', 'json', 'docx', 'doc', "odt",'mp3','wav','ogg','m4a','mp4','webm','mov'}
socketio = SocketIO(cors_allowed_origins="*")
def admin_required(f):
    """
    Декоратор ограничения доступа.

    Разрешает доступ к роуту только:
    - авторизованным пользователям
    - пользователям с ролью admin
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(403)

        if current_user.role != "admin":
            abort(403)

        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



def create_app():
    """
    Фабрика приложения Flask.

    Создаёт и настраивает приложение:
    - подключает конфиг
    - инициализирует БД
    - настраивает login_manager
    - подключает CSRF защиту
    - регистрирует роуты
    """
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(os.path.dirname(__file__))

    app = Flask ( __name__,
        template_folder=os.path.join(base_path, "templates"),
        static_folder=os.path.join(base_path, "static"),
        
    )   


    app.config.from_object(Config)

    # нормальные пути для exe
    upload_folder = os.path.join(base_path, "static", "uploads", "files")
    avatar_folder = os.path.join(base_path, "static", "uploads", "avatars")

    app.config["UPLOAD_FOLDER"] = upload_folder
    app.config["AVATAR_FOLDER"] = avatar_folder

    os.makedirs(upload_folder, exist_ok=True)
    os.makedirs(avatar_folder, exist_ok=True)
    migrate = Migrate(app, site)
    # Инициализация CSRF защиты
    csrf = CSRFProtect(app)

    
    site.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.login_message_category = 'danger'
    login_manager.login_message = "Пожалуйста, войдите в систему для доступа к странице."
    login_manager.init_app(app)


    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        site.create_all()
    

    @app.route('/')
    @app.route('/index')
    @login_required
    def index():
        """
    Главная страница сайта.

    Показывает последние загруженные файлы.
    Файлы группируются по batch_id если
    были загружены одной партией.
    """

        # Получаем последние 100 файлов
        all_files = File.query.order_by(File.upload_time.desc()).limit(100).all()
        
        # Чтобы группировка работала корректно, данные ДОЛЖНЫ быть отсортированы по ключу группировки
        # Используем batch_id, если он есть, иначе используем уникальную строку на основе ID файла
        def get_group_key(f):
            return f.batch_id if f.batch_id else f"single_{f.id}"

        # Сортируем: сначала по ключу группы, затем внутри группы по времени (на всякий случай)
        all_files.sort(key=lambda x: (get_group_key(x), x.upload_time), reverse=True)
        
        grouped_list = []
        # Группируем по нашему ключу
        for key, group in groupby(all_files, key=get_group_key):
            grouped_list.append(list(group))
            
        # Сортируем уже готовый список групп по самой свежей дате внутри каждой группы
        grouped_list.sort(key=lambda g: g[0].upload_time, reverse=True)
            
        return render_template('index.html', grouped_files=grouped_list)
   

    @app.route('/profile/<int:user_id>')
    @login_required
    def profile(user_id):
        # Логика получения пользователя и его файлов
        user = User.query.get_or_404(user_id)
        # Используем пагинацию
        page = request.args.get('page', 1, type=int)
        files = File.query.filter_by(user_id=user.id)\
                    .order_by(File.upload_time.desc())\
                    .paginate(page=page, per_page=5)
        
        return render_template('profile.html', user=user, files=files,now=datetime.utcnow())

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """
    Регистрация нового пользователя.

    Проверяет:
    - уникальность username
    - корректность email
    - длину пароля

    После регистрации создаёт запись в БД.
    """
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        if request.method == 'POST':
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")

            if not username or not email or len(password) < 6:
                flash('Нправильный ввод', 'danger')
                return redirect(url_for('register'))

            if User.query.filter_by(username=username).first():
                flash('Такое имя уже есть', 'danger')
                return redirect(request.url)
            
            user = User(username=username, email=email)
            user.set_password(password)
            site.session.add(user)
            site.session.commit()
            flash('Аккаунт создан!', 'success')
            return redirect(url_for('login'))
        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """
    Авторизация пользователя.

    Проверяет:
    - email
    - пароль
    - блокировку аккаунта
    - двухфакторную аутентификацию (2FA).
    """
        if current_user.is_authenticated:
            return redirect(url_for('index'))

        if request.method == 'POST':
            email = request.form.get("email", "")
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email).first()

            if user and user.is_blocked:
                flash("Аккаунт заблокирован администратором", "danger")
                return redirect(url_for("login"))

            if user and user.check_password(password):
                if user.two_factor_enabled:
                    session["2fa_user_id"] = user.id
                    return redirect(url_for("two_factor_verify"))

                login_user(user, remember=True)
                return redirect(url_for('index'))

            flash('Вход не удался. Проверьте данные.', 'danger')

        return render_template('login.html')

    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('index'))

    @app.route("/upload", methods=["GET", "POST"])
    @login_required
    def upload():
        """
    Загрузка файлов на сервер.

    Поддерживает множественную загрузку.
    Файлы сохраняются в UPLOAD_FOLDER
    с уникальным именем (UUID).
    """

        if request.method == "POST":

            if "files" not in request.files:
                flash("Файлы не найдены", "error")
                return redirect(request.url)

            files = request.files.getlist("files")

            if not files or files[0].filename == "":
                flash("Файлы не выбраны", "error")
                return redirect(request.url)

            upload_folder = app.config["UPLOAD_FOLDER"]
            os.makedirs(upload_folder, exist_ok=True)

            allowed_extensions = ALLOWED_EXTENSIONS

            batch_id = str(uuid.uuid4()) if len(files) > 1 else None

            for file in files:

                original_name = file.filename  # UTF-8 сохраняем как есть

                if "." not in original_name:
                    flash(f"Файл {original_name} без расширения", "error")
                    continue

                ext = original_name.rsplit(".", 1)[-1].lower()

                if ext not in allowed_extensions:
                    flash(f"Файл {original_name} запрещён", "error")
                    continue

                # Генерируем UUID имя
                storage_name = f"{uuid.uuid4().hex}.{ext}"
                file_path = os.path.join(upload_folder, storage_name)

                file.save(file_path)

                

                description = request.form.get("description")

                new_file = File(
                    filename=original_name,
                    storage_filename=storage_name,
                    user_id=current_user.id,
                    batch_id=batch_id,
                    description=description
                )

                site.session.add(new_file)

            site.session.commit()

            flash("Файлы успешно загружены", "success")
            return redirect(url_for("index"))

        return render_template("upload.html")

     
    
    @app.route('/profile/edit', methods=['GET', 'POST'])
    @login_required
    def edit_profile():
        """
    Страница профиля пользователя.

    Отображает:
    - информацию о пользователе
    - список его файлов
    - используется пагинация.
    """
        if request.method == 'POST':
            # Получение данных из формы
            username = request.form.get('username')
            email = request.form.get('email')
            bio = request.form.get('bio')

            # Проверка на уникальность имени, если оно изменилось
            if username != current_user.username:
                user_exists = User.query.filter_by(username=username).first()
                if user_exists:
                    flash('Это имя пользователя уже занято.', 'error')
                    return redirect(url_for('edit_profile'))

            # Обновление полей объекта пользователя
            current_user.username = username
            current_user.email = email
            current_user.bio = bio

            try:
                site.session.commit()
                flash('Профиль успешно обновлен!', 'success')
                return redirect(url_for('profile', user_id=current_user.id))
            except Exception as e:
                site.session.rollback()
                flash('Произошла ошибка при сохранении изменений.', 'error')
        
        return render_template('edit_profile.html', user=current_user)

    @app.template_filter('linebreaksbr')
    def linebreaksbr_filter(s):
        if not s:
            return ""
        lines = escape(s).replace('\n', Markup('<br>'))
        return lines

    @app.route('/view/<int:file_id>')
    @login_required
    def view_file(file_id):
        """
    Просмотр файла.

    В зависимости от типа файла:
    - текстовые файлы читаются и выводятся
    - docx конвертируется в текст
    - изображения / медиа показываются через HTML.
    """
        file_record = File.query.get_or_404(file_id)
        content = None
        
        # Важно: используем storage_filename для поиска на диске
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_record.storage_filename)
        
        file_size = 0
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
        
        # Определяем расширение для предпросмотра текста
        ext = file_record.filename.lower()

        # -------- TXT и код --------
        text_extensions = ('.txt', '.py', '.js', '.css', '.html', '.json')

        if any(ext.endswith(x) for x in text_extensions):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                content = f"Не удалось прочитать файл: {e}"

        # -------- DOCX --------
        elif ext.endswith('.docx'):
            if Document is None:
                content = "Предпросмотр DOCX недоступен: библиотека не загружена."
        else:
            try:
                doc = Document(file_path)
                paragraphs = [p.text for p in doc.paragraphs if p.text.strip() != ""]
                content = "\n".join(paragraphs)

                if not content.strip():
                    content = "Документ пуст."
            except Exception as e:
                content = f"Не удалось прочитать DOCX: {e}"

        return render_template('view_file.html', file=file_record, content=content, file_size=file_size)
    
    @app.route('/raw/<int:file_id>')
    @login_required
    def get_raw_file(file_id):
        file_record = File.query.get_or_404(file_id)
        # Используем storage_filename, если оно есть, иначе filename
        name_to_serve = file_record.storage_filename or file_record.filename
        return send_from_directory(app.config['UPLOAD_FOLDER'], name_to_serve)

    @app.route('/download/<int:file_id>')
    @login_required
    def download_file(file_id):
        """
    Скачивание файла.

    Отдаёт файл с сервера пользователю
    с оригинальным именем.
    """
        file_data = File.query.get_or_404(file_id)
        name_to_serve = file_data.storage_filename or file_data.filename
        # Но при скачивании отдаем ОРИГИНАЛЬНОЕ имя пользователю
        return send_from_directory(
            app.config['UPLOAD_FOLDER'], 
            name_to_serve, 
            as_attachment=True, 
            download_name=file_data.filename
    )

    
    @app.route('/edit_avatar', methods=['POST'])
    @login_required
    def edit_avatar():

        if 'avatar' not in request.files:
            return {"message": "Файл не найден"}, 400
        file = request.files['avatar']
        if file.filename == '':
            return {"message": "Файл не выбран"}, 400
        ext = file.filename.rsplit(".", 1)[1].lower()
        allowed = {"png", "jpg", "jpeg", "gif", "webp"}
        if ext not in allowed:
            return {"message": "Недопустимый формат"}, 400
        try:
            avatar_folder = app.config["AVATAR_FOLDER"]
            # ---------- GIF ----------
            if ext == "gif":
                filename = f"user_{current_user.id}.gif"
                save_path = os.path.join(avatar_folder, filename)
                file.save(save_path)
            # ---------- обычные изображения ----------
            else:
                if Image is None:
                    return {"message": "Pillow не установлен"}, 500
                img = Image.open(file)
                img = img.convert("RGB")
                filename = f"user_{current_user.id}.jpg"
                save_path = os.path.join(avatar_folder, filename)
                img.save(save_path, "JPEG", quality=90)
            current_user.avatar = filename
            site.session.commit()
            return {"message": "Успешно"}, 200
        except Exception as e:
            print("Avatar error:", e)
            return {"message": "Ошибка обработки изображения"}, 400
    
    @app.route('/avatar/<filename>')
    def avatar(filename):
        return send_from_directory(app.config["AVATAR_FOLDER"], filename)
    
    @app.route("/share/<int:file_id>")
    @login_required
    def share_file(file_id):
        file = File.query.get_or_404(file_id)

        if file.user_id != current_user.id:
            abort(403)

        if not file.share_token:
            file.share_token = secrets.token_urlsafe(32)
            file.is_public = True
            site.session.commit()

        link = url_for("public_file", token=file.share_token, _external=True)

        return render_template("share.html", file=file, link=link)
    @app.route("/s/<token>")
    def public_file(token):
        file = File.query.filter_by(share_token=token, is_public=True).first_or_404()

        return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        file.storage_filename,
        as_attachment=True,
        download_name=file.filename
    )

    @app.route("/search")
    @login_required
    def search():
        query = request.args.get("q")
        files = File.query.filter(
            File.user_id == current_user.id,
            File.filename.ilike(f"%{query}%")
        ).all()

        return render_template("search.html", files=files, query=query)

    @app.route('/delete/<int:file_id>', methods=['POST'])
    @login_required
    def delete_file(file_id):
        """
    Удаление файла пользователем.

    Проверяет владельца файла,
    затем удаляет:
    - файл с диска
    - запись из базы данных.
    """
        file_record = File.query.get_or_404(file_id)
        
        # Проверка прав доступа
        if file_record.user_id != current_user.id:
            abort(403)

        # Путь к физическому файлу
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_record.storage_filename)
        
        # Удаляем файл с диска
        if os.path.exists(file_path):
            os.remove(file_path)

        # Удаляем запись из базы
        site.session.delete(file_record)
        site.session.commit()
        
        return redirect(url_for('index'))    

    # Часовой пояс (можешь поменять если нужно)
    LOCAL_TIMEZONE = ZoneInfo("Europe/Moscow")

    @app.template_filter("localtime")
    def localtime_filter(dt):
        if dt is None:
            return ""

        # если время без timezone (naive)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        local_dt = dt.astimezone(LOCAL_TIMEZONE)
        return local_dt.strftime("%d.%m.%Y %H:%M")
    
    @app.route("/2fa", methods=["GET", "POST"])
    def two_factor_verify():
        user_id = session.get("2fa_user_id")

        if not user_id:
            return redirect(url_for("login"))

        user = User.query.get(user_id)

        if not user or not user.two_factor_secret:
            return redirect(url_for("login"))

        if request.method == "POST":
            code = request.form.get("code", "").strip()
            totp = pyotp.TOTP(user.two_factor_secret)

            if totp.verify(code, valid_window=1):
                login_user(user, remember=True)
                session.pop("2fa_user_id", None)
                flash("Успешная двухфакторная аутентификация", "success")
                return redirect(url_for("index"))

            flash("Неверный код", "danger")

        return render_template("2fa.html")
    
    @app.route("/enable-2fa")
    @login_required
    def enable_2fa():
        # Генерируем временный секрет
        secret = pyotp.random_base32()
        session["temp_2fa_secret"] = secret  # сохраняем В СЕССИИ, а не в базе

        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(
            name=current_user.email,
            issuer_name="YourSite"
        )

        # Генерация QR-кода
        img = qrcode.make(uri)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()

        return render_template("enable_2fa.html", qr_code=qr_base64)
   
    @app.route("/confirm-2fa", methods=["POST"])
    @login_required
    def confirm_2fa():
        code = request.form.get("code", "").strip()
        secret = session.get("temp_2fa_secret")

        if not secret:
            flash("Ошибка инициализации 2FA", "danger")
            return redirect(url_for("profile", user_id=current_user.id))

        totp = pyotp.TOTP(secret)

        if totp.verify(code, valid_window=1):
            current_user.two_factor_secret = secret
            current_user.two_factor_enabled = True
            site.session.commit()

            session.pop("temp_2fa_secret", None)

            flash("2FA успешно включена", "success")
            return redirect(url_for("profile", user_id=current_user.id))

        flash("Неверный код", "danger")
        return redirect(url_for("enable_2fa"))

    @app.route("/disable-2fa", methods=["POST"])
    @login_required
    def disable_2fa():
        current_user.two_factor_enabled = False
        current_user.two_factor_secret = None
        site.session.commit()
        flash("2FA отключена", "success")
        return redirect(url_for("profile", user_id=current_user.id))
       
    @app.route("/set_theme", methods=["POST"])
    @login_required
    def set_theme():
     

        # Получаем JSON данные от fetch()
        data = request.get_json()

        if not data:
            return {"status": "error", "message": "Нет данных"}, 400

        theme = data.get("theme")

        # Разрешённые темы
        allowed = ["default", "red", "black", "cherry","neon", "custom"]

        # Проверка — чтобы нельзя было отправить произвольное значение
        if theme not in allowed:
            return {"status": "error", "message": "Недопустимая тема"}, 400

        # Сохраняем выбранную тему
        current_user.theme = theme

        # Если тема кастомная — сохраняем цвета
        if theme == "custom":
            current_user.custom_accent = data.get("accent")
            current_user.custom_bg = data.get("bg")
            current_user.custom_container = data.get("container")

        # Сохраняем изменения в БД
        site.session.commit()

        return {"status": "ok"}
    
    
    @app.route("/admin")
    @login_required
    @admin_required
    def admin():
        """
        Админ панель.

        Показывает:
        - список пользователей
        - статистику сайта
        - графики регистраций и загрузок.
        """
        users = User.query.order_by(User.id.desc()).all()
        total_users = User.query.count()
        total_files = File.query.count()

        last_week = datetime.utcnow() - timedelta(days=7)

        registrations_raw = (
            site.session.query(
                func.date(User.created_at),
                func.count(User.id)
            )
            .filter(User.created_at >= last_week)
            .group_by(func.date(User.created_at))
            .all()
        )

        registrations = [
            [str(row[0]), int(row[1])]
            for row in registrations_raw
        ]

        uploads_raw = (
            site.session.query(
                func.date(File.upload_time),
                func.count(File.id)
            )
            .filter(File.upload_time >= last_week)
            .group_by(func.date(File.upload_time))
            .all()
        )

        uploads = [
            [str(row[0]), int(row[1])]
            for row in uploads_raw
        ]

        roles_raw = (
            site.session.query(
                User.role,
                func.count(User.id)
            )
            .group_by(User.role)
            .all()
        )

        roles = [
            [str(row[0]), int(row[1])]
            for row in roles_raw
        ]

        return render_template(
            "admin.html",
            users=users,
            total_users=total_users,
            total_files=total_files,
            registrations=registrations,
            uploads=uploads,
            roles=roles
        )

    @app.route("/admin/toggle-block/<int:user_id>", methods=["POST"])
    @login_required
    @admin_required
    def admin_toggle_block(user_id):
        user = User.query.get_or_404(user_id)

        if user.id == current_user.id:
            flash("Нельзя заблокировать самого себя", "danger")
            return redirect(url_for("admin"))

        user.is_blocked = not user.is_blocked
        site.session.commit()

        flash("Статус пользователя изменён", "success")
        return redirect(url_for("admin"))
        
    @app.route("/admin/delete-user/<int:user_id>", methods=["POST"])
    @login_required
    @admin_required
    def admin_delete_user(user_id):
        """
        Удаление пользователя администратором.

        Удаляет:
        - все файлы пользователя
        - записи файлов в БД
        - сам аккаунт пользователя.
        """
        user = User.query.get_or_404(user_id)

        if user.id == current_user.id:
            flash("Нельзя удалить самого себя", "danger")
            return redirect(url_for("admin"))

        # Получаем все файлы пользователя
        files = File.query.filter_by(user_id=user.id).all()

        for file in files:

            # удаляем файл с диска
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.storage_filename)

            if os.path.exists(file_path):
                os.remove(file_path)

            # удаляем запись из БД
            site.session.delete(file)

        # теперь удаляем пользователя
        site.session.delete(user)

        site.session.commit()

        flash("Пользователь и его файлы удалены", "success")
        return redirect(url_for("admin"))
    
    @app.route("/admin/files")
    @login_required
    @admin_required
    def admin_all_files():
        files = File.query.order_by(File.upload_time.desc()).all()
        return render_template("admin_files.html", files=files)
    
    @app.route("/admin/delete-file/<int:file_id>", methods=["POST"])
    @login_required
    @admin_required
    def admin_delete_file(file_id):
            
        file_record = File.query.get_or_404(file_id)

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_record.storage_filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        site.session.delete(file_record)
        site.session.commit()

        flash("Файл удалён администратором", "success")
        return redirect(request.referrer or url_for("admin"))
    
    @app.before_request
    def check_if_blocked():
        """
        Глобальная проверка перед каждым запросом.

        Если пользователь заблокирован —
        ему показывается страница blocked.html.
        """

        # Если пользователь не авторизован — ничего не делаем
        if not current_user.is_authenticated:
            return

        # Разрешаем logout, чтобы человек мог выйти
        allowed_routes = ["logout", "static"]

        if request.endpoint in allowed_routes:
            return

        # Если пользователь заблокирован — показываем страницу
        if current_user.is_blocked:
            return render_template("blocked.html"), 403
    
    @socketio.on("send_message")
    def handle_chat_message(data):

        if not current_user.is_authenticated:
            return

        message = data.get("message", "").strip()
        reply = data.get("reply")

        if not message:
            return

        username = current_user.username

        avatar = current_user.avatar
        if avatar:
            avatar_url = url_for("avatar", filename=avatar)
        else:
            avatar_url = url_for("static", filename="default_avatar.png")

        payload = {
            "username": username,
            "avatar": avatar_url,
            "message": message,
            "reply": reply,
            "time": datetime.utcnow().strftime("%H:%M")
        }

        send(payload, broadcast=True)


    @app.route("/lan-chat")
    @login_required
    def lan_chat():
        return render_template("lan_chat.html")


    socketio.init_app(app)

    return app





    