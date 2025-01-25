# QuizUp - Сервис для проведения опросов

**QuizUp** - это веб-сервис, предназначенный для создания, проведения и анализа опросов. Он позволяет пользователям легко создавать опросы различных типов, делиться ими с аудиторией и проводить интерактивные опросы.

## Возможности

*   **Создание опросов:**
    *   Поддержка различных типов вопросов:
        *   Выбор одного ответа
        *   Выбор нескольких ответов
        *   Открытый текстовый ответ
    *   Предпросмотр опроса перед публикацией
*   **Управление опросами:**
    *   Сохранение черновиков
    *   Публикация и деактивация опросов
    *   Редактирование существующих опросов
    *   Удаление опросов
*   **Участие в опросах:**
    *   Удобный интерфейс для прохождения опросов
    *   Возможность анонимного участия
    *   Отправка результатов опроса
*   **Управление пользователями:**
    *   Регистрация новых пользователей
    *   Вход в систему

## Роли пользователей

В системе QuizUp предусмотрены следующие роли:

2.  **Создатель опросов (`creator`)**:
    *   Может создавать, редактировать и удалять только собственные опросы.
    *   Может просматривать результаты опроса.
    *   Не имеет доступа к опросам, созданным другими пользователями.
    *   Не имеет доступа к настройкам системы.
3.  **Участник опросов (`participant`)**:
    *   Может только проходить опросы.
    *   Не имеет доступа к результатам опросов.


## Инструкция по развертыванию QuizUp

### Предварительные требования

Перед началом убедитесь, что на устройстве, где вы планируете развернуть приложение, выполнены следующие условия:

1.  **Установлен Python:** На устройстве должен быть установлен Python версии 3.8 или выше.
2.  **Установлен pip:** Вместе с Python обычно устанавливается менеджер пакетов `pip`. Убедитесь, что он также установлен.
3. **Установлен Git**: `Git` нужен для клонирования репозитория.

### Шаги по развертыванию

1.  **Клонирование репозитория:**

    Откройте терминал или командную строку и выполните следующую команду, чтобы склонировать репозиторий с кодом приложения:
    ```bash
    git clone <адрес_вашего_репозитория>
    cd <название_папки_репозитория>
    ```
    Замените `<адрес_вашего_репозитория>` на URL вашего репозитория QuizUp и `<название_папки_репозитория>` на название папки репозитория.

2.  **Создание виртуального окружения (рекомендуется):**
    Создание виртуального окружения позволит изолировать зависимости вашего проекта от остальной системы.

    ```bash
    python -m venv venv
    ```
    
    Активируйте виртуальное окружение:
    - Для Windows:
      ```bash
      venv\Scripts\activate
      ```
    - Для macOS и Linux:
      ```bash
      source venv/bin/activate
      ```
3.  **Установка зависимостей:**
    Установите необходимые библиотеки, используя `pip` и файл `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```
   
4.  **Настройка базы данных:**
   
    Приложение использует базу данных SQLite. Убедитесь, что она создана и настроена. При первом запуске она должна создаться автоматически.
  
5.  **Запуск приложения:**
    Запустите приложение Flask, выполнив в терминале команду:
    ```bash
    python app.py
    ```
    После запуска вы увидите сообщение о том, что сервер Flask запущен, и адрес, по которому можно получить доступ к приложению (обычно это `http://127.0.0.1:5000`).

6.  **Доступ к приложению:**
    Откройте веб-браузер на том же устройстве и введите адрес, указанный в терминале, чтобы получить доступ к приложению.
7. **Доступ к приложению с другого устройства (в локальной сети):**
    Чтобы получить доступ к приложению с другого устройства в локальной сети, вам потребуется узнать IP-адрес устройства, на котором запущено приложение.
    * На macOS или Linux:
      ```bash
        ipconfig getifaddr en0
      ```
    * На Windows:
      ```bash
      ipconfig | findstr IPv4
      ```
     После получения IP-адреса запустите приложение, передав его в качестве хоста:
     ```bash
        python app.py --host 0.0.0.0
     ```
   Теперь к приложению можно будет получить доступ с другого устройства в локальной сети, используя в браузере `http://<ip_адрес>:5000`.

  8. ** Разворачивание в production (для постоянной работы) **

Для запуска приложения в production среде используйте **Gunicorn** или любой другой WSGI-сервер.

1. Установите Gunicorn:

   ```bash
   pip install gunicorn
   ```

2. Запустите приложение через Gunicorn:

   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

### Дополнительная информация

*   **Настройка секретного ключа:** В файле `app.py` есть строка `app.config['SECRET_KEY'] = 'your_secret_key'`. Рекомендуется заменить `'your_secret_key'` на более сложный и уникальный ключ. Можно сгенерировать случайную строку с помощью, например, `secrets.token_hex(16)`
*   **Обновление приложения:** Если вы внесли изменения в код, вам потребуется перезапустить сервер Flask, чтобы изменения вступили в силу.
*  **Завершение работы:**
   Чтобы остановить приложение, вернитесь в терминал и нажмите `Ctrl + C`.

### Возможные проблемы

*   **Проблемы с зависимостями:** Если вы столкнулись с ошибками при установке зависимостей, убедитесь, что у вас установлены последние версии `pip` и `setuptools`.
*   **Проблемы с портами:** Если порт 5000 уже занят, вы можете указать другой порт при запуске приложения, используя параметр `--port`. Например:
    ```bash
     python app.py --port 5001
    ```
   В этом случае, вы должны будете использовать `http://127.0.0.1:5001` (или `http://<ip_адрес>:5001` в случае доступа с другого устройства) для доступа к приложению.

*   **Проблемы с базой данных:**
1. Убедитесь, что на устройстве установлен **SQLite** (должен быть предустановлен вместе с Python).
2. Создайте базу данных (если её ещё нет). Для этого выполните команду:

   ```bash
   flask db upgrade
   ```

   Либо выполните миграцию вручную, если она требуется:

   ```bash
   python -c "from app import db; db.create_all()"
   ```

---
*   **Настройка переменных окружения:**
1. Создайте файл `.env` в корне проекта и добавьте необходимые переменные окружения:

   ```plaintext
   SECRET_KEY=your_secret_key
   SQLALCHEMY_DATABASE_URI=sqlite:///polls.db
   WTF_CSRF_ENABLED=True
   ```

2. Убедитесь, что `SECRET_KEY` заменён на уникальную строку.

---
*   **Дополнительные Проблемы:**
#### Генерация QR-кодов
Приложение использует библиотеку **qrcode** для генерации QR-кодов. Убедитесь, что зависимости установлены, и Flask имеет доступ к статическим файлам.

#### Socket.IO
Приложение поддерживает real-time взаимодействие через **Flask-SocketIO**. Для production среды установите:

```bash
pip install eventlet
```

И запустите сервер с использованием **eventlet**:

```bash
python -m flask run --with-threads --host=0.0.0.0
```
---

# Форма обратной связи 
Мы ценим ваше мнение и всегда стремимся улучшать наш сервис. Если у вас есть вопросы, предложения или вы столкнулись с проблемами, пожалуйста, заполните эту форму обратной связи.

https://docs.google.com/forms/d/e/1FAIpQLScwR2BVs5gVW4zKYAW9IvDxl_LjvF1AW2uEMzvkgxlXNc9jYg/viewform?usp=dialog
