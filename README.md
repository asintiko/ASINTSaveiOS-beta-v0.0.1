ASINTsave iOS

Описание

ASINTsave iOS — это Telegram‑бот для сохранения и управления медиа‑файлами. Бот позволяет пользователям удобно сохранять фотографии, видео, документы и другие типы медиа из сообщений Telegram, а затем быстро находить и просматривать их при необходимости. Проект находится в стадии бета‑тестирования (версия 0.0.1).

Функциональность
	•	Сохранение медиа‑файлов: бот поддерживает сохранение фотографий, видео, аудио, документов, стикеров и других типов медиа из чатов Telegram.
	•	Категоризация: сохранённые файлы можно организовывать по категориям для удобства управления.
	•	Поиск и просмотр: реализован удобный поиск по сохранённым медиа и возможность быстрого просмотра нужных файлов.
	•	Работа в группах и личных сообщениях: бот может использоваться как в личных сообщениях, так и будучи добавленным в групповые чаты (при наличии необходимых прав).

Установка и настройка

Требования
	•	Python 3.8 или выше
	•	pip (менеджер пакетов Python)
	•	Telegram Bot API Token – токен доступа к Bot API (получается у официального бота @BotFather)

Шаги по установке
	1.	Клонирование репозитория
    

	2.	Создание виртуального окружения
    python -m venv venv
source venv/bin/activate  # Для Linux/Mac
# или
venv\Scripts\activate     # Для Windows
	3.	Установка зависимостей
    pip install -r requirements.txt

	4.	Настройка конфигурации
	•	Переименуйте файл .env.example в .env (если файл примера отсутствует, создайте новый файл .env в корневой папке).
	•	Отредактируйте файл .env, указав необходимые параметры. Минимально требуется задать токен вашего бота Telegram:

TOKEN="<ваш токен от BotFather>"
DATABASE_URL="sqlite+aiosqlite:///./savebot_koala.db"
RUN_VIA_POLLING="true"

Примечание: значения по умолчанию, как показано выше, настроят использование локальной базы данных SQLite (savebot_koala.db) и запуск бота в режиме опроса (long polling). При необходимости вы можете изменить эти параметры (например, для использования вебхуков, удалённой БД и т.д.).

	5.	Запуск бота
    python main.py

    Использование

После запуска бота вы можете взаимодействовать с ним через Telegram:
	1.	Начало работы: откройте диалог со своим ботом в Telegram (найдите его по имени пользователя, указанному при регистрации у BotFather) и отправьте команду /start для начала работы.
	2.	Сохранение медиа: перешлите боту сообщение с медиа‑файлом или используйте тект в ответ на сообщение с медиа, чтобы сохранить файл.
	3.	Доступ к сохранённым файлам: используйте команду /list, чтобы вывести список всех ваших сохранённых медиа, или отправьте команду /help для получения справки по управлению сохранениями и другим возможностям бота.
Поддержка и контакты

Если у вас возникли вопросы или проблемы при использовании бота, вы можете связаться с автором проекта asintiko через следующие каналы:
	•	Telegram: @KulacodmYT

Лицензия

Проект распространяется под лицензией MIT. Подробности можно найти в файле LICENSE.

English Version

Description

ASINTsave iOS is a Telegram bot for saving and managing media files. The bot enables users to conveniently save photos, videos, documents and other types of media from Telegram messages and then quickly find and view them when needed. The project is currently in beta testing (version 0.0.1).

Features
	•	Media saving: The bot supports saving photos, videos, audio, documents, stickers, and other media types from Telegram chats.
	•	Categorization: Saved files can be organized into categories for easier management.
	•	Search and viewing: A convenient search is implemented across saved media, along with the ability to quickly view the required files.
	•	Works in groups and private messages: The bot can be used both in private messages and when added to group chats (with the necessary permissions).

Installation and Setup

Requirements
	•	Python 3.8 or higher
	•	pip (Python package manager)
	•	Telegram Bot API Token – an access token for the Bot API (obtained from the official @BotFather bot)

Installation Steps
	1.	Clone the repository
    	2.	Create a virtual environment
        	3.	Install dependencies
            4.	Configure
	•	Rename the .env.example file to .env (if the example file is missing, create a new .env in the project root).
	•	Edit the .env file to set the required parameters. At minimum, specify your Telegram bot token

Usage

After launching the bot, you can interact with it via Telegram:
	1.	Getting started: open a chat with your bot in Telegram (find it by the username you set via BotFather) and send /start to receive a welcome message and initial instructions.
	2.	Saving media: forward a message with media to the bot or reply with /save to the message containing media to save the file.
	3.	Accessing saved files: use the /list command to show a list of all your saved media, or send /help to get instructions on managing your saved items and other bot capabilities.

Support and Contact

If you have questions or issues using the bot, you can contact the project author asintiko through the following channels:
	•	Telegram: @KulacodmYT

License

This project is distributed under the MIT license. See the LICENSE file for details.