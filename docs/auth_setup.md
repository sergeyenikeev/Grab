# Настройка Gmail OAuth и IMAP (Mail.ru/Yandex)

## 0) Какие файлы должны появиться
- `D:\\p\\Grab\\.env` - ваши локальные настройки.
- `D:\\p\\Grab\\secrets\\gmail_client_secret.json` - OAuth client secret для Gmail.
- `D:\\p\\Grab\\data\\auth\\gmail_token.json` - токен после `grab auth`.

## 1) Подготовка .env
1. Скопируйте шаблон:
   - PowerShell: `Copy-Item .env.example .env`
2. Откройте `.env` и заполните значения:
   - `GMAIL_OAUTH_CLIENT_SECRET_PATH=D:\\p\\Grab\\secrets\\gmail_client_secret.json`
   - `GMAIL_OAUTH_TOKEN_PATH=D:\\p\\Grab\\data\\auth\\gmail_token.json`
   - `GMAIL_ACCOUNT=your_gmail@gmail.com`
   - `MAILRU_IMAP_USER=your_mailru@mail.ru`
   - `MAILRU_IMAP_PASSWORD=<mailru_app_password>`
   - `YANDEX_IMAP_USER=your_yandex_1@yandex.ru`
   - `YANDEX_IMAP_PASSWORD=<yandex_app_password_1>`
   - `YANDEX_IMAP_USER_2=your_yandex_2@yandex.ru`
   - `YANDEX_IMAP_PASSWORD_2=<yandex_app_password_2>`

## 2) Gmail OAuth: как получить `gmail_client_secret.json`
1. Перейдите в Google Cloud Console: `https://console.cloud.google.com/`.
2. В меню слева выберите `IAM & Admin` -> `Create a Project` (или кликните по имени проекта справа и выберите существующий).
3. После выбора проекта откройте `APIs & Services` -> `Library`, найдите `Gmail API` и нажмите `Enable`.
4. Перейдите в `APIs & Services` -> `OAuth consent screen`:
   - выберите User Type `External`, нажмите `Create`;
   - заполните `App name`, `User support email`, задайте `Developer contact email`;
   - в `Test users` добавьте ваш Gmail (например, `your.name@gmail.com`).
5. Перейдите в `APIs & Services` -> `Credentials` -> `Create Credentials` -> `OAuth client ID`:
   - тип приложения `Desktop app`;
   - имя: `Grab Sync CLI` (или любое удобное);
   - нажмите `Create`, затем `Download JSON`.
6. Сохраните скачанный файл как `D:\\p\\Grab\\secrets\\gmail_client_secret.json`.
7. Этот JSON — секрет приложения. Храните его только локально и не коммитьте. Можно ориентироваться на шаблон `D:\\p\\Grab\\secrets\\gmail_client_secret.example.json`.
8. Для запуска `grab auth` убедитесь, что путь в `.env` совпадает с `GMAIL_OAUTH_CLIENT_SECRET_PATH` и что ваш браузер может открыть `http://localhost` (токен сохраняется в `GMAIL_OAUTH_TOKEN_PATH`).

## 3) Mail.ru IMAP + app password
1. Перейдите в веб-интерфейс Mail.ru (`https://account.mail.ru/security`).
2. Включите двухфакторную аутентификацию (если она не включена, пароли приложений недоступны).
3. В разделе "Пароли приложений" нажмите "Создать пароль", выберите "Другое приложение" и дайте имя типа "GrabSync".
4. Скопируйте сгенерированный пароль и вставьте его в `.env`:
   - `MAILRU_IMAP_PASSWORD=<mailru_app_password>`
5. Убедитесь, что в настройках почты на вкладке `https://e.mail.ru/settings/tabs/imap` включён доступ по IMAP и указан порт `993`.

## 4) Yandex IMAP + app password (два ящика)
1. Откройте страницу безопасности Яндекс ID: `https://passport.yandex.com/profile`.
2. Если ещё не включена двухфакторная аутентификация, нажмите "Включить" на вкладке "Безопасность". Без 2FA создание паролей приложений невозможно.
3. Перейдите в раздел `Пароли приложений` и добавьте новый пароль с названием, например, "Grab-yandex-1".
4. Скопируйте сгенерированный пароль и запишите:
   - `YANDEX_IMAP_USER=your_yandex_1@yandex.ru`
   - `YANDEX_IMAP_PASSWORD=<yandex_app_password_1>`
5. Чтобы подключить второй ящик, повторите шаги 3-4 и запишите секреты с суффиксом `_2`:
   - `YANDEX_IMAP_USER_2=your_yandex_2@yandex.ru`
   - `YANDEX_IMAP_PASSWORD_2=<yandex_app_password_2>`
6. Проверьте, что IMAP включён на странице `https://mail.yandex.com/settings/imap` и статус "IMAP и POP3" — активен.
7. При необходимости добавляйте дополнительные ящики (`_3`, `_4`, ..., `_10`) по той же схеме.

## 5) Проверка авторизации
1. Выполните:
   - `python -m grab.cli auth`
2. Ожидаемый результат:
   - `Gmail OAuth OK` и путь к токену;
   - `IMAP OK` для mailru и для каждого yandex-ящика.

## 6) Первый sync
1. Базовый запуск:
   - `python -m grab.cli sync --source email --since 2024-01-01 --media download`
2. Если хотите захватить всю историю:
   - `python -m grab.cli sync --source email --since 1980-01-01 --media download`

## 7) Быстрая диагностика
- Проверить окружение: `python -m grab.cli doctor`
- Если OAuth сломан: удалите `D:\\p\\Grab\\data\\auth\\gmail_token.json` и повторите `auth`.
- Если IMAP ошибка `AUTHENTICATIONFAILED`: почти всегда неверный app password.

## Пример .env (тестовые данные)
```dotenv
GRAB_HOME=D:\\p\\Grab
GRAB_DB_PATH=D:\\p\\Grab\\data\\grab.sqlite3
GRAB_LOG_DIR=D:\\p\\Grab\\logs

GMAIL_OAUTH_CLIENT_SECRET_PATH=D:\\p\\Grab\\secrets\\gmail_client_secret.json
GMAIL_OAUTH_TOKEN_PATH=D:\\p\\Grab\\data\\auth\\gmail_token.json
GMAIL_ACCOUNT=test.user.demo@gmail.com

MAILRU_IMAP_HOST=imap.mail.ru
MAILRU_IMAP_PORT=993
MAILRU_IMAP_USER=test_mailru_demo@mail.ru
MAILRU_IMAP_PASSWORD=mailru_app_password_demo_123456

YANDEX_IMAP_HOST=imap.yandex.ru
YANDEX_IMAP_PORT=993
YANDEX_IMAP_USER=test_yandex_demo_1@yandex.ru
YANDEX_IMAP_PASSWORD=yandex_app_password_demo_111111

YANDEX_IMAP_HOST_2=imap.yandex.ru
YANDEX_IMAP_PORT_2=993
YANDEX_IMAP_USER_2=test_yandex_demo_2@yandex.ru
YANDEX_IMAP_PASSWORD_2=yandex_app_password_demo_222222
```
