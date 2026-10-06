import os
import secrets
from pathlib import Path
from uuid import uuid4

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from flask_login import LoginManager, current_user, login_required, login_user, logout_user
from PIL import Image, UnidentifiedImageError
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from models import Item, User, db


def create_app(config=None):
    app = Flask(__name__)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    key_file = Path(app.instance_path) / 'secret.key'
    if not key_file.exists():
        key_file.write_text(secrets.token_hex(32), encoding='utf-8')
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY') or key_file.read_text(encoding='utf-8'),
        SQLALCHEMY_DATABASE_URI='sqlite:///anabada.db',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=8 * 1024 * 1024,
        UPLOAD_FOLDER=str(Path(app.static_folder) / 'uploads'),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
    )
    if config:
        app.config.update(config)
    Path(app.config['UPLOAD_FOLDER']).mkdir(parents=True, exist_ok=True)
    db.init_app(app)
    login = LoginManager(app)
    login.login_view = 'login'
    login.login_message = '로그인 후 이용해 주세요.'

    @login.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id)) if user_id.isdigit() else None

    @app.context_processor
    def template_helpers():
        session.setdefault('csrf_token', secrets.token_hex(32))
        return {'csrf_token': session['csrf_token']}

    @app.before_request
    def csrf_protect():
        if request.method == 'POST':
            expected = session.get('csrf_token', '')
            supplied = request.form.get('csrf_token', '')
            if not expected or not secrets.compare_digest(expected, supplied):
                abort(400, description='요청이 만료되었습니다. 페이지를 새로고침해 주세요.')

    def owned_item(item_id):
        item = db.get_or_404(Item, item_id)
        if item.author_id != current_user.id:
            abort(403)
        return item

    def remove_image(filename):
        if filename:
            (Path(app.config['UPLOAD_FOLDER']) / filename).unlink(missing_ok=True)

    def save_image(upload):
        if not upload or not upload.filename:
            return None
        # Validate the original suffix: secure_filename strips Korean-only stems.
        if Path(upload.filename.strip()).suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
            raise ValueError('JPG, PNG, WEBP 사진만 업로드할 수 있습니다.')
        try:
            with Image.open(upload.stream) as original:
                original.load()
                original.thumbnail((1600, 1600))
                image = original.convert('RGB')
                name = uuid4().hex + '.jpg'
                image.save(Path(app.config['UPLOAD_FOLDER']) / name, 'JPEG', quality=88)
                return name
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError, Image.DecompressionBombWarning):
            raise ValueError('읽을 수 없는 이미지입니다. 다른 사진을 선택해 주세요.')

    @app.route('/')
    def index():
        q = request.args.get('q', '').strip()[:100]
        free = request.args.get('free') == '1'
        query = Item.query
        if q:
            escaped = q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
            query = query.filter(or_(Item.title.ilike(f'%{escaped}%', escape='\\'), Item.description.ilike(f'%{escaped}%', escape='\\')))
        if free:
            query = query.filter(Item.price == 0)
        pagination = query.order_by(Item.created_at.desc(), Item.id.desc()).paginate(page=request.args.get('page', 1, type=int), per_page=12, error_out=False)
        return render_template('index.html', items=pagination.items, pagination=pagination, q=q, free=free)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            password = request.form.get('password', '')
            if not 2 <= len(username) <= 40 or not 8 <= len(password) <= 128:
                flash('이름은 2~40자, 비밀번호는 8~128자로 입력해 주세요.', 'danger')
            else:
                user = User(username=username)
                user.set_password(password)
                db.session.add(user)
                try:
                    db.session.commit()
                    login_user(user)
                    flash('환영합니다! 첫 번째 나눔을 시작해 보세요.', 'success')
                    return redirect(url_for('index'))
                except IntegrityError:
                    db.session.rollback()
                    flash('이미 사용 중인 이름입니다.', 'danger')
        return render_template('auth.html', registering=True)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        if request.method == 'POST':
            user = User.query.filter_by(username=request.form.get('username', '').strip()).first()
            if user and user.check_password(request.form.get('password', '')):
                login_user(user)
                return redirect(url_for('index'))
            flash('이름 또는 비밀번호를 확인해 주세요.', 'danger')
        return render_template('auth.html', registering=False)

    @app.post('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('index'))

    @app.get('/items/<int:item_id>')
    def item_detail(item_id):
        return render_template('item_detail.html', item=db.get_or_404(Item, item_id))

    @app.route('/items/new', methods=['GET', 'POST'])
    @app.route('/items/<int:item_id>/edit', methods=['GET', 'POST'])
    @login_required
    def item_form(item_id=None):
        item = owned_item(item_id) if item_id else None
        if request.method == 'POST':
            try:
                title = request.form.get('title', '').strip()
                description = request.form.get('description', '').strip()
                try:
                    price = 0 if request.form.get('free') else int(request.form.get('price', '0'))
                except ValueError:
                    raise ValueError('가격을 정수로 입력해 주세요.')
                if not 1 <= len(title) <= 100 or not 1 <= len(description) <= 5000:
                    raise ValueError('제목은 1~100자, 설명은 1~5,000자로 입력해 주세요.')
                if not 0 <= price <= 1_000_000_000:
                    raise ValueError('가격은 0~10억 원 사이로 입력해 주세요.')
                new_image = save_image(request.files.get('image'))
                old_image = item.image_filename if item else None
                if not item:
                    item = Item(author_id=current_user.id)
                    db.session.add(item)
                item.title, item.description, item.price = title, description, price
                if new_image:
                    item.image_filename = new_image
                db.session.commit()
                if new_image:
                    remove_image(old_image)
                flash('물품을 저장했습니다.', 'success')
                return redirect(url_for('item_detail', item_id=item.id))
            except ValueError as error:
                flash(str(error), 'danger')
        return render_template('item_form.html', item=item)

    @app.post('/items/<int:item_id>/status')
    @login_required
    def item_status(item_id):
        item = owned_item(item_id)
        item.status = '거래완료' if item.status == '거래가능' else '거래가능'
        db.session.commit()
        flash('거래 상태를 변경했습니다.', 'success')
        return redirect(url_for('item_detail', item_id=item.id))

    @app.post('/items/<int:item_id>/delete')
    @login_required
    def item_delete(item_id):
        item = owned_item(item_id)
        filename = item.image_filename
        db.session.delete(item)
        db.session.commit()
        remove_image(filename)
        flash('물품을 삭제했습니다.', 'success')
        return redirect(url_for('index'))

    @app.errorhandler(413)
    def too_large(error):
        return render_template('error.html', code=413, message='사진은 8MB보다 작은 파일로 선택해 주세요.'), 413

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    def error_page(error):
        messages = {400: error.description, 403: '등록자만 이 작업을 할 수 있습니다.', 404: '찾으시는 페이지가 없습니다.'}
        return render_template('error.html', code=error.code, message=messages[error.code]), error.code

    with app.app_context():
        db.create_all()
    return app


if __name__ == '__main__':
    create_app().run(debug=os.environ.get('FLASK_DEBUG') == '1')
