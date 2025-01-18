from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    polls = db.relationship('Poll', backref='user', lazy=True)

class Poll(db.Model):
    __tablename__ = 'polls'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    entry_code = db.Column(db.String(6), unique=True)
    is_active = db.Column(db.Boolean, default=False)
    current_question_index = db.Column(db.Integer, default=0)  # Индекс текущего вопроса
    questions = db.relationship('Question', backref='poll', lazy='dynamic')  # Changed to dynamic
    created_at = db.Column(db.DateTime, default=datetime.utcnow)  # Добавляем время создания опроса

class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    poll_id = db.Column(db.Integer, db.ForeignKey('polls.id'), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    is_closed = db.Column(db.Boolean, default=False) # Добавляем флаг для закрытия вопроса
    options = db.relationship('Option', backref='question', lazy=True)
    answers = db.relationship('UserAnswer', backref='question', lazy=True)

class Option(db.Model):
    __tablename__ = 'options'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(100), nullable=False)
    correct = db.Column(db.Boolean, default=False)  # For closed questions (optional)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    votes = db.Column(db.Integer, default=0) #Not use in this version

class UserAnswer(db.Model):
    __tablename__ = 'user_answers'  # Explicit table name
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # Исправлено
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'))
    answer = db.Column(db.String(255))  # Store the user's selected answer (or text for open questions)
    option_id = db.Column(db.Integer, db.ForeignKey('options.id'), nullable=True) #For closed questions