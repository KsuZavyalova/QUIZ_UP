from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FieldList, RadioField, BooleanField, TextAreaField, \
    HiddenField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError

class RegisterForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Подтвердите пароль', validators=[DataRequired(), EqualTo('password', message='Пароли должны совпадать')])
    submit = SubmitField('Зарегистрироваться')

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class PollForm(FlaskForm):
    title = StringField('Название опроса', validators=[DataRequired(), Length(min=1, max=200)])
    submit = SubmitField('Создать Опрос')
    csrf_token = HiddenField()

class OpenQuestionForm(FlaskForm):
    text = StringField('Текст вопроса', validators=[DataRequired(), Length(min=1, max=10000)])
    submit = SubmitField('Добавить Вопрос')

class ClosedQuestionForm(FlaskForm):
    text = TextAreaField('Введите вопрос здесь', validators=[DataRequired()]) # Using TextAreaField for question text
    options = FieldList(StringField('Вариант ответа', validators=[DataRequired()]), min_entries=2) # FieldList for options, at least 2 entries
    correct_answers = FieldList(BooleanField('Правильный ответ'), min_entries=2) # FieldList for correct answers, matching options
    next = SubmitField('Далее')
    finish = SubmitField('Завершить')