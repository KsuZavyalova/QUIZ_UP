from flask import Flask, request, render_template, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import true
from forms import PollForm, RegisterForm, LoginForm, OpenQuestionForm, ClosedQuestionForm
from models import db, User, Poll, Question, Option, UserAnswer
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_socketio import SocketIO, emit, join_room, leave_room
import secrets
import string
import qrcode
from io import BytesIO
import base64
import logging

app = Flask(__name__, static_folder='static', static_url_path='/static')

# --- Configuration ---
app.config['WTF_CSRF_ENABLED'] = True
app.config['SECRET_KEY'] = 'your_secret_key'  # Замените на свой секретный ключ
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///polls.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- Initialize Extensions ---
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'index'
socketio = SocketIO(app)

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Flask-Login User Loader ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Database Initialization (within app context) ---
with app.app_context():
    db.create_all()

# --- Helper Functions ---
def generate_entry_code():
    """Генерируем уникальный код подключения (6 символов)."""
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(secrets.choice(alphabet) for _ in range(6))
        if Poll.query.filter_by(entry_code=code).first() is None:
            return code

def generate_qr_code(entry_code):
    """Генерируем QR-код, вшивая в него URL с GET-параметром ?code=<entry_code>."""
    join_url = url_for('join_poll_route', _external=True)  # Полный URL
    data_to_encode = f"{join_url}?code={entry_code}"
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
    qr.add_data(data_to_encode)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    img_base64 = base64.b64encode(img_io.getvalue()).decode()
    return img_base64


@app.route('/')
def root():
    if current_user.is_authenticated:
        return redirect(url_for('page'))
    return redirect(url_for('index'))

@app.route('/page')
@login_required
def page():
    """Главная страница для авторизованного пользователя."""
    polls = Poll.query.filter_by(user_id=current_user.id).all()
    return render_template('page.html', polls=polls)

@app.route('/registration', methods=['GET', 'POST'])
def registration():
    form = RegisterForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Имя пользователя уже существует. Пожалуйста, выберите другое.', 'danger')
            return redirect(url_for('registration'))
        hashed_pw = generate_password_hash(form.password.data, method='pbkdf2:sha256')
        new_user = User(username=form.username.data, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash('Вы успешно зарегистрировались!', 'success')
        return redirect(url_for('index'))
    elif form.errors:
        for field, errors in form.errors.items():
            for error in errors:
                if field == 'confirm_password' and error == 'Пароли должны совпадать':
                    flash('Пароли не совпадают.', 'danger')
                else:
                    flash(error, 'danger')
    return render_template('registration.html', form=form)

@app.route('/index', methods=['GET', 'POST'])
def index():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('page'))
        else:
            flash('Неправильное имя пользователя или пароль.', 'danger')
    return render_template('index.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы.', 'success')
    return redirect(url_for('index'))

# --- Создание опроса и добавление вопросов ---
@app.route('/input_name_quiz', methods=['GET', 'POST'])
@login_required
def input_name_quiz():
    form = PollForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            title = form.title.data
            try:
                new_poll = Poll(
                    title=title,
                    user_id=current_user.id,
                    entry_code=generate_entry_code()  # <-- Генерируем код подключения
                )
                db.session.add(new_poll)
                db.session.commit()
                # Сохраняем id опроса в сессии, чтобы знать, к какому опросу добавлять вопросы.
                session['current_poll_id'] = new_poll.id
                return redirect(url_for('choose_question'))
            except Exception as e:
                db.session.rollback()
                flash(f'Ошибка при создании опроса: {str(e)}', 'danger')
    return render_template('input_name_quiz.html', form=form)

@app.route('/choose_question')
@login_required
def choose_question():
    poll_id = session.get('current_poll_id')
    if not poll_id:
        flash('Сначала создайте опрос.', 'warning')
        return redirect(url_for('input_name_quiz'))
    return render_template('choose_question.html', poll_id=poll_id)


# Добавьте этот маршрут в ваш Flask-код
@app.route('/edit_survey/<int:poll_id>')
@login_required
def edit_survey(poll_id):
    """Страница редактирования опроса со списком всех вопросов"""
    poll = Poll.query.get_or_404(poll_id)

    # Проверка прав доступа
    if poll.user_id != current_user.id:
        return "Unauthorized", 403

    # Получаем вопросы отсортированные по порядку
    questions = poll.questions.order_by(Question.order).all()

    return render_template('edit_survey.html',
                           poll=poll,
                           questions=questions)


# Добавьте эти маршруты в ваш Flask-код
@app.route('/delete_question/<int:question_id>', methods=['POST'])
@login_required
def delete_question(question_id):
    """Удаление вопроса"""
    question = Question.query.get_or_404(question_id)
    poll = question.poll

    # Проверка прав доступа
    if poll.user_id != current_user.id:
        return "Unauthorized", 403

    try:
        # Удаляем связанные ответы и варианты
        UserAnswer.query.filter_by(question_id=question.id).delete()
        if question.type == 'closed':
            Option.query.filter_by(question_id=question.id).delete()

        # Удаляем сам вопрос
        db.session.delete(question)
        db.session.commit()
        flash('Вопрос успешно удален', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении вопроса: {str(e)}', 'danger')

    return redirect(url_for('edit_survey', poll_id=poll.id))


@app.route('/edit_question/<int:question_id>', methods=['GET', 'POST'])
@login_required
def edit_question(question_id):
    """Редактирование существующего вопроса"""
    question = Question.query.get_or_404(question_id)
    poll = question.poll

    # Проверка прав доступа
    if poll.user_id != current_user.id:
        return "Unauthorized", 403

    # В зависимости от типа вопроса используем соответствующую форму
    if question.type == 'open':
        form = OpenQuestionForm(obj=question)
    else:
        form = ClosedQuestionForm(obj=question)
        # Заполняем варианты ответов
        for i, option in enumerate(question.options):
            form.options[i].text.data = option.text
            form.correct_answers[i].data = option.correct

    if form.validate_on_submit():
        try:
            question.text = form.text.data

            if question.type == 'closed':
                # Обновляем варианты ответов
                for i, option in enumerate(question.options):
                    option.text = form.options[i].text.data
                    option.correct = form.correct_answers[i].data

            db.session.commit()
            flash('Вопрос успешно обновлен', 'success')
            return redirect(url_for('edit_survey', poll_id=poll.id))

        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении вопроса: {str(e)}', 'danger')

    return render_template(f'input_{question.type}_question.html',
                           form=form,
                           edit_mode=True,
                           question=question)

@app.route('/input_open_question', methods=['GET', 'POST'])
@login_required
def input_open_question():
    poll_id = session.get('current_poll_id')
    if not poll_id:
        flash('Сначала создайте опрос.', 'warning')
        return redirect(url_for('input_name_quiz'))

    form = OpenQuestionForm()
    if form.validate_on_submit():
        last_q = Question.query.filter_by(poll_id=poll_id).order_by(Question.order.desc()).first()
        next_order = (last_q.order + 1) if last_q else 1
        new_q = Question(
            text=form.text.data,
            type='open',
            poll_id=poll_id,
            order=next_order
        )
        db.session.add(new_q)
        db.session.commit()
        flash('Открытый вопрос добавлен!', 'success')

        if 'next' in request.form:
            return redirect(url_for('choose_question'))
        elif 'finish' in request.form:
            flash('Все вопросы добавлены!', 'success')
            return redirect(url_for('page'))

    return render_template('input_open_question.html', form=form)

@app.route('/input_base_question', methods=['GET', 'POST'])
@login_required
def input_base_question():
    poll_id = session.get('current_poll_id')
    if not poll_id:
        flash('Сначала создайте опрос.', 'warning')
        return redirect(url_for('input_name_quiz'))

    form = ClosedQuestionForm()
    if request.method == 'POST':
        # Настройка поля FieldList для вариантов ответа.
        form.options.min_entries = 2  # Минимум 2 варианта
        form.options.max_entries = 10 # Максимум 10 вариантов
        # Корректные ответы
        form.correct_answers.min_entries = 2
        form.correct_answers.max_entries = 10

        if form.validate_on_submit():
            last_q = Question.query.filter_by(poll_id=poll_id).order_by(Question.order.desc()).first()
            next_order = (last_q.order + 1) if last_q else 1

            new_q = Question(
                text=form.text.data,
                type='closed',
                poll_id=poll_id,
                order=next_order
            )
            db.session.add(new_q)
            db.session.commit()

            # Сохраняем варианты
            for i in range(10): #  10 вариантов в форме
                option_text_key = f'options-{i}'
                correct_answer_key = f'correct_answers-{i}'

                option_text = request.form.get(option_text_key)
                is_correct_str = request.form.get(correct_answer_key)
                # Проверка, является ли вариант ответа правильным
                is_correct = (is_correct_str is not None and is_correct_str in ['on','y'])

                if option_text and option_text.strip(): #  пустые не сохраняем
                    opt = Option(
                        text=option_text.strip(),
                        question_id=new_q.id,
                        correct=is_correct
                    )
                    db.session.add(opt)
            db.session.commit()

            flash('Закрытый вопрос добавлен!', 'success')

            if 'next' in request.form:
                return redirect(url_for('choose_question'))
            elif 'finish' in request.form:
                flash('Все вопросы добавлены!', 'success')
                return redirect(url_for('page'))

    return render_template('input_base_question.html', form=form)

@app.route('/join_poll', methods=['GET'])
def join_poll_route():
    code = request.args.get('code')
    poll = Poll.query.filter_by(entry_code=code).first()
    if poll:
        # Сохраняем в сессии, чтобы знать, к какому опросу подключены
        session['poll_id'] = poll.id
        return redirect(url_for('participant_show_question'))
    else:
        flash('Неверный код!', 'danger')
        return redirect(url_for('input_entery_code'))

# --- Маршрут с QR-кодом ---
@app.route('/qr/<int:poll_id>')
@login_required
def show_qr(poll_id):
    """Отображаем страницу, на которой ведущий видит QR-код и кнопку «Начать опрос»."""
    poll = Poll.query.get_or_404(poll_id)
    if poll.user_id != current_user.id:
        return "Unauthorized", 403
    # Генерируем QR-картинку
    qr_code_image = generate_qr_code(poll.entry_code)
    return render_template('qr.html', poll=poll, qr_code_image=qr_code_image)


@app.route('/start_poll/<entry_code>')
@login_required
def start_poll_route_by_code(entry_code):
    """Начать опрос, если в URL передаётся entry_code (например, U8FDIJ)."""
    # Ищем опрос по коду, а не по ID
    poll = Poll.query.filter_by(entry_code=entry_code).first_or_404()

    # Проверяем, что текущий пользователь — владелец
    if poll.user_id != current_user.id:
        return "Unauthorized", 403

    # Сбрасываем опрос перед началом
    reset_poll(poll.id)

    # Начинаем новый опрос
    poll.is_active = True
    poll.current_question_index = 0
    db.session.commit()

    # Уведомляем всех по SocketIO (если нужно)
    socketio.emit('poll_started', {'poll_id': poll.id, 'is_active': True}, room=poll.entry_code)

    # Переадресуем на show_question, где <poll_id> — это числовой ID
    return redirect(url_for('show_question', poll_id=poll.id))

# --- Участник вводит код (если не сканирует QR) ---
@app.route('/input_entery_code', methods=['GET','POST'])
def input_entery_code():
    """
    If a person does not scan the QR but wants to manually enter the code,
    let them go to /input_entery_code, enter the code -> we find the Poll -> redirect to /participant_show_question
    """
    if request.method == 'POST':
        entry_code = request.form.get('entry_code')
        poll = Poll.query.filter_by(entry_code=entry_code).first()
        if poll:
            session['poll_id'] = poll.id  # Remember which poll
            return redirect(url_for('participant_show_question'))  # Go to displaying the current question
        else:
            flash('Incorrect code!', 'danger')
    return render_template('input_entery_code.html')

@app.route('/participant_show_question')
def participant_show_question():
    """
    Участник заходит сюда (уже имея session['poll_id']),
    мы ему показываем тот же текущий вопрос poll.current_question_index.
    Внешне — та же страница, что у ведущего, но без кнопок "Следующий вопрос".
    """
    poll_id = session.get('poll_id')
    if not poll_id:
        flash('Сначала введите код!', 'danger')
        return redirect(url_for('input_entery_code'))

    poll = Poll.query.get_or_404(poll_id)
    if not poll.is_active:
        return "Опрос ещё не начался или уже завершён."

    current_question = poll.questions.order_by(Question.order).offset(poll.current_question_index).first()
    if not current_question:
        return "Вопросов нет или они закончились."

    # Можно отрендерить тот же шаблон show_open_question/show_closed_question,
    # но передать флаг, что мы участники (чтобы не показывать кнопки «Далее»).
    if current_question.type == 'open':
        return render_template('show_open_question.html', question=current_question, poll=poll, is_host=False)
    else:
        return render_template('show_closed_question.html', question=current_question, poll=poll, is_host=False)


# --- Переход (у ведущего) к отображению текущего вопроса ---
@app.route('/show_question/<int:poll_id>')
@login_required
def show_question(poll_id):
    """Ведущий смотрит на текущий вопрос (полная страница)."""
    poll = Poll.query.get_or_404(poll_id)
    if poll.user_id != current_user.id:
        return "Unauthorized", 403

    current_question = poll.questions.order_by(Question.order).offset(poll.current_question_index).first()
    if current_question:
        # Передадим is_host=True, чтобы в шаблоне показывать кнопки «Закрыть вопрос», «Следующий вопрос».
        if current_question.type == 'open':
            return render_template('show_open_question.html', question=current_question, poll=poll, is_host=True)
        else:
            return render_template('show_closed_question.html', question=current_question, poll=poll, is_host=True)
    else:
        poll.is_active = False
        db.session.commit()
        return "Все вопросы закончились. Опрос завершен!"

@app.route('/next_question/<int:poll_id>', methods=['GET','POST'])
@login_required
def next_question(poll_id):
    """Ведущий нажимает «Далее» — переключаемся на следующий вопрос."""
    poll = Poll.query.get_or_404(poll_id)
    if poll.user_id != current_user.id:
        return "Unauthorized", 403

    if poll.current_question_index < poll.questions.count() - 1:
        poll.current_question_index += 1
        db.session.commit()
        # Можно также emit'ить событие через SocketIO, чтобы клиенты (участники) автоматически обновили страницу
        socketio.emit('question_changed', {'poll_id': poll_id}, room=poll.entry_code)  # Добавлено
    else:
        # Если вопросов больше нет
        poll.is_active = False
        db.session.commit()
        socketio.emit('poll_ended', {'poll_id': poll_id}, room=poll.entry_code) # Добавлено
        return "Все вопросы пройдены, опрос завершен"

    return redirect(url_for('show_question', poll_id=poll.id))

# --- Socket.IO Event Handlers (если нужно real-time) ---
@socketio.on('connect')
def handle_connect():
    print('Client connected:', request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected:', request.sid)

@socketio.on('join_poll')
def handle_join_poll(data):
    """ Пример, если хотите, чтобы участники присоединялись в комнату SocketIO """
    entry_code = data['entry_code']
    poll = Poll.query.filter_by(entry_code=entry_code).first()
    if not poll or not poll.is_active:
        emit('error', {'message': 'Invalid or inactive poll'}, room=request.sid)
        return
    join_room(entry_code)
    session['poll_id'] = poll.id
    emit('poll_joined', {'poll_id': poll.id, 'current_question': poll.current_question_index}, room=request.sid)

@socketio.on('start_poll')
def handle_start_poll(data):
    """Ведущий начинает опрос заново"""
    poll_id = data['poll_id']
    poll = Poll.query.get(poll_id)
    if poll and poll.user_id == current_user.id:
        poll.is_active = True
        poll.current_question_index = 0
        db.session.commit()
        emit('poll_started', {
            'poll_id': poll_id,
            'first_question': poll.current_question_index
        }, room=poll.entry_code)

@socketio.on('show_next_question')
def handle_next_question(data):
    """Ведущий переключает на следующий вопрос"""
    poll_id = data['poll_id']
    poll = Poll.query.get(poll_id)
    if poll and poll.user_id == current_user.id:
        if poll.current_question_index < poll.questions.count() - 1:
            poll.current_question_index += 1
            db.session.commit()
            current_question = poll.questions.order_by(Question.order).offset(poll.current_question_index).first()
            emit('question_changed', {
                'question_index': poll.current_question_index,
                'question_data': {
                    'id': current_question.id,
                    'text': current_question.text,
                    'type': current_question.type,
                    'options': [{'id': opt.id, 'text': opt.text} for opt in current_question.options] if current_question.type == 'closed' else None
                }
            }, room=poll.entry_code)

@socketio.on('submit_answer')
def handle_submit_answer(data):
    """
    Если хотите принимать ответы по SocketIO.
    """
    question_id = data['question_id']
    answer_text = data.get('answer')
    option_id = data.get('option_id')
    user_id = session.get('user_id') or request.sid  #  уникальный идентификатор участника
    poll_id = session.get('poll_id')  # Добавлено получение poll_id из сессии

    question = Question.query.get(question_id)
    if not question or question.poll_id != poll_id or question.is_closed:  # Добавлена проверка poll_id
        emit('error', {'message': 'Question closed or not found'})
        return

    existing_answer = UserAnswer.query.filter_by(user_id=user_id, question_id=question_id).first()
    if existing_answer:
        return  #  уже отвечал

    new_answer = UserAnswer(user_id=user_id, question_id=question_id)
    if question.type == 'open':
        new_answer.answer = answer_text
    else:
        if option_id is None:
            return
        new_answer.option_id = option_id

    db.session.add(new_answer)
    db.session.commit()

    emit('answer_submitted', {'user_id': user_id, 'question_id': question_id}, room=poll.entry_code)

@socketio.on('reopen_question')
def reopen_question(data):
    poll_id = data['poll_id']
    question_id = data['question_id']
    poll = Poll.query.get(poll_id)
    question = Question.query.get(question_id)

    if poll and question and poll.user_id == current_user.id:
        question.is_closed = False
        db.session.commit()
        emit('question_reopened', {'question_id': question_id}, room=poll.entry_code)

@socketio.on('close_question')
def handle_close_question(data):
    """Ведущий закрывает текущий вопрос."""
    poll_id = data['poll_id']
    poll = Poll.query.get(poll_id)
    user_id = session.get('user_id') # Получаем user_id из сессии
    if not poll or user_id != poll.user_id:
        emit('error', {'message': 'Unauthorized'})
        return

    current_question = poll.questions[poll.current_question_index]
    current_question.is_closed = True
    db.session.commit()
    emit('question_closed', {'question_id': current_question.id}, room=poll.entry_code)

@app.route('/reset_poll/<int:poll_id>')
@login_required
def reset_poll(poll_id):
    """Сброс опроса для повторного запуска."""
    poll = Poll.query.get_or_404(poll_id)
    if poll.user_id != current_user.id:
        return "Unauthorized", 403

    # Сбрасываем состояние опроса
    poll.is_active = False
    poll.current_question_index = 0

    # Сбрасываем состояние вопросов и удаляем ответы
    for question in poll.questions:
        question.is_closed = False
        UserAnswer.query.filter_by(question_id=question.id).delete()

    db.session.commit()
    flash('Опрос сброшен и готов к повторному запуску.', 'success')
    return redirect(url_for('page'))  # Или куда вам нужно

# --- Отображение результатов ---
@app.route('/results/<int:poll_id>')
@login_required
def results(poll_id):
    """Ведущий просматривает результаты опроса."""
    poll = Poll.query.get_or_404(poll_id)
    if poll.user_id != current_user.id:
        return "Unauthorized", 403

    results_data = {}

    for q in poll.questions:
        q_answers = UserAnswer.query.filter_by(question_id=q.id).all()

        # Блок, который положим в results_data[q.id]
        # будет по-разному выглядеть в зависимости от типа вопроса
        question_result = {
            'question_text': q.text,
            'type': q.type,
        }

        if q.type == 'closed':
            # Создаём структуру для каждого варианта ответа
            options_dict = {}
            for opt in q.options:
                options_dict[opt.id] = {
                    'text': opt.text,
                    'correct': opt.correct,
                    'count': 0
                }

            # Считаем, сколько раз каждый вариант выбран
            for ans in q_answers:
                if ans.option_id in options_dict:
                    options_dict[ans.option_id]['count'] += 1

            # Превратим в список для удобной итерации в шаблоне
            question_result['options'] = list(options_dict.values())

        else:
            # Открытый вопрос — просто собираем ответы и считаем их
            open_answers = {}
            for ans in q_answers:
                text = ans.answer or ""
                open_answers[text] = open_answers.get(text, 0) + 1

            question_result['open_answers'] = open_answers

        results_data[q.id] = question_result

    return render_template('results.html', poll=poll, results=results_data)

# Главная точка входа
if __name__ == '__main__':
    socketio.run(app, debug=True)
