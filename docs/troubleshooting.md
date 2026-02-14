# Troubleshooting

## Полная настройка Gmail OAuth + IMAP
- Подробная пошаговая инструкция: `docs/auth_setup.md`
- Пример OAuth JSON: `secrets/gmail_client_secret.example.json`
- Пример `.env`: `.env.example`

## Gmail OAuth: не открывается авторизация
- Проверьте путь `GMAIL_OAUTH_CLIENT_SECRET_PATH` в `.env`.
- Убедитесь, что в Google Cloud создан OAuth Client ID для Desktop App.

## Gmail OAuth: invalid_grant
- Удалите старый токен `data/auth/gmail_token.json` и выполните `grab auth` заново.

## IMAP Mail.ru/Yandex: AUTHENTICATIONFAILED
- Используйте app-password, а не пароль от аккаунта.
- Проверьте, что IMAP включен в настройках почты.

## Sync не находит письма
- Проверьте `GRAB_EMAIL_KEYWORDS`.
- Запустите без `--since` для первичной проверки.

## Ошибки SSL/сертификата IMAP
- Проверьте корректность хоста/порта (`imap.mail.ru:993`, `imap.yandex.ru:993`).

## Медиа не скачивается
- URL может требовать авторизацию/подписанные cookies.
- В этом случае в MVP сохраняются вложения и доступные прямые ссылки.

## Дубли
- Запустите `grab dedupe`.
- Проверьте корректность входных `order_id` и шаблонов парсера.
