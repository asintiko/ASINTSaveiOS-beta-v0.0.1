"""Localized messages and button labels for the bot."""

from __future__ import annotations

from typing import Dict

DEFAULT_LANGUAGE = "ru"

AGREEMENT_URLS = {
    "ru": "https://telegra.ph/Polzovatelskoe-soglashenie-proekta-09-28",
    "en": "https://telegra.ph/Here-is-the-English-translation-of-the-User-Agreement-for-the-ASINT-SaveiOS-project-09-29",
}

TUTORIAL_URLS = {
    "ru": "https://telegra.ph/Kak-ispolzovat-i-ustanovit-bota-09-29",
    "en": "https://telegra.ph/How-to-install-and-use-the-Asint-SAVEiOS-09-29",
}

MESSAGES: Dict[str, Dict[str, str]] = {
    "language_prompt": {
        "ru": "Пожалуйста, выберите язык интерфейса.",
        "en": "Please choose your preferred language.",
    },
    "language_updated": {
        "ru": "Язык интерфейса успешно обновлен: {language}",
        "en": "Language updated: {language}",
    },
    "language_unchanged": {
        "ru": "Уже используется язык: {language}",
        "en": "You are already using: {language}",
    },
    "agreement_prompt": {
        "ru": "Перед началом работы примите пользовательское соглашение.",
        "en": "Before you start, please accept the user agreement.",
    },
    "agreement_reminder": {
        "ru": "Чтобы продолжить, подтвердите, что прочитали пользовательское соглашение.",
        "en": "To continue, please confirm that you have read the user agreement.",
    },
    "agreement_confirmed": {
        "ru": "Спасибо! Вы приняли пользовательское соглашение и можете продолжить работу.",
        "en": "Thank you! The user agreement has been accepted and you can continue.",
    },
    "agreement_already_confirmed": {
        "ru": "Пользовательское соглашение уже принято.",
        "en": "The user agreement was already accepted.",
    },
    "start_welcome": {
        "ru": (
            "<b>🎉 Добро пожаловать в AsintSave iOS!</b>\n\n"
            "<blockquote><i>Ваш надежный помощник для сохранения важных моментов в Telegram. "
            "Мы заботимся о безопасности ваших данных и конфиденциальности.</i></blockquote>\n\n"
            "<b>Ключевые возможности:</b>\n"
            "• Автоматическое сохранение одноразовых медиа (фото, видео, кружки, голосовые сообщения).\n"
            "• Сохранение медиафайлов с таймером.\n"
            "• Отслеживание и сохранение удаленных и измененных сообщений.\n"
            "• Создание уникальных анимаций и стикеров (скоро!).\n\n"
            "<blockquote><i>Для начала работы, пожалуйста, ознакомьтесь с инструкцией, нажав на кнопку ниже.</i></blockquote>"
        ),
        "en": (
            "<b>🎉 Welcome to AsintSave iOS!</b>\n\n"
            "<blockquote><i>Your trusted assistant for saving important Telegram moments. "
            "We keep your data safe and private.</i></blockquote>\n\n"
            "<b>Key features:</b>\n"
            "• Automatically saves self-destructing media (photos, videos, round videos, voice messages).\n"
            "• Captures media with timers.\n"
            "• Tracks and saves deleted or edited messages.\n"
            "• Builds unique animations and stickers (coming soon!).\n\n"
            "<blockquote><i>To get started, open the guide using the button below.</i></blockquote>"
        ),
    },
    "business_mode_required": {
        "ru": "У бота нет доступа к бизнес-сообщениям. Включите его в настройках BotFather и попробуйте снова.",
        "en": "This bot lacks Business Mode access. Enable it in BotFather settings and try again.",
    },
    "user_banned": {
        "ru": "Ваш доступ к боту ограничен администратором. Обратитесь в поддержку.",
        "en": "An administrator restricted your access. Please contact support.",
    },
    "start_required": {
        "ru": "Отправьте команду /start, чтобы начать работу с ботом.",
        "en": "Send /start to begin using the bot.",
    },
    "settings_intro": {
        "ru": "Настройте язык интерфейса и откройте пользовательское соглашение через меню ниже.",
        "en": "Adjust your language preference or open the user agreement using the menu below.",
    },
    "settings_section_title": {
        "ru": "Настройки",
        "en": "Settings",
    },
    "profile_title": {
        "ru": "<b>👤 Профиль</b>",
        "en": "<b>👤 Profile</b>",
    },
    "profile_plan": {
        "ru": "Тариф: {plan}",
        "en": "Plan: {plan}",
    },
    "profile_subscription_active": {
        "ru": "Подписка активна до {date} (осталось {time_left}).",
        "en": "Subscription active until {date} (time left: {time_left}).",
    },
    "profile_subscription_no_expiry": {
        "ru": "Подписка без даты окончания.",
        "en": "Subscription has no end date.",
    },
    "profile_subscription_inactive": {
        "ru": "Подписка не активна.",
        "en": "Subscription is inactive.",
    },
    "profile_period": {
        "ru": "Период: {period}",
        "en": "Billing period: {period}",
    },
    "profile_period_week": {
        "ru": "недельный",
        "en": "weekly",
    },
    "profile_period_month": {
        "ru": "месячный",
        "en": "monthly",
    },
    "profile_period_unknown": {
        "ru": "не указан",
        "en": "not set",
    },
    "profile_media_header": {
        "ru": "📸 Медиа",
        "en": "📸 Media",
    },
    "profile_notifications_header": {
        "ru": "🔔 Уведомления",
        "en": "🔔 Notifications",
    },
    "profile_limits_unlimited": {
        "ru": "Без ограничений.",
        "en": "Unlimited.",
    },
    "profile_limits_line": {
        "ru": "{scope}: {used}/{limit} (осталось {remaining})",
        "en": "{scope}: {used}/{limit} (remaining {remaining})",
    },
    "profile_limits_line_unlimited": {
        "ru": "{scope}: без ограничений",
        "en": "{scope}: unlimited",
    },
    "profile_limits_reset": {
        "ru": "Сброс: {date}",
        "en": "Reset: {date}",
    },
    "profile_limits_scope_week": {
        "ru": "Неделя",
        "en": "Week",
    },
    "profile_limits_scope_month": {
        "ru": "Месяц",
        "en": "Month",
    },
    "profile_time_part_day": {
        "ru": "{value} дн.",
        "en": "{value} d",
    },
    "profile_time_part_hour": {
        "ru": "{value} ч.",
        "en": "{value} h",
    },
    "profile_time_part_minute": {
        "ru": "{value} мин.",
        "en": "{value} min",
    },
    "profile_time_less_minute": {
        "ru": "<1 мин.",
        "en": "<1 min",
    },
    "add_bot_missing_token": {
        "ru": "Укажите токен бота: /add_bot <TOKEN>",
        "en": "Please provide a bot token: /add_bot <TOKEN>",
    },
    "add_bot_invalid_token": {
        "ru": "Неверный формат токена. Попробуйте снова.",
        "en": "Invalid token format. Please try again.",
    },
    "create_bot_instructions": {
        "ru": (
            "<b>Для создания зеркала </b><b>@SaveMod_bot</b><b> следуйте инструкции</b> 👇 \n\n"
            "<blockquote>1. Перейдите в @BotFather\n\n"
            "2. Напишите /newbot, отправьте желаемое имя бота (оно может быть любым).\n\n"
            "3. Отправьте @Username бота. Он должен заканчиваться на «Bot», пример: testnetbot.\n\n"
            "4. Напишите в @BotFather /mybots и выберите созданного бота.\n\n"
            "5. Нажмите «Bot Settings» → «Business Mode» и включите его.\n\n"
            "6. «Back to Settings» → «Back to Bot» → «API Token» — скопируйте токен и пришлите сюда.</blockquote>"
        ),
        "en": (
            "<b>To create a mirror of </b><b>@SaveMod_bot</b><b>, follow these steps</b> 👇 \n\n"
            "<blockquote>1. Open @BotFather.\n\n"
            "2. Send /newbot and provide any bot name.\n\n"
            "3. Send the bot @Username ending with “Bot”, for example: testnetbot.\n\n"
            "4. Send /mybots in @BotFather and pick the newly created bot.\n\n"
            "5. Tap “Bot Settings” → “Business Mode” and switch it on.\n\n"
            "6. “Back to Settings” → “Back to Bot” → “API Token” — copy the token and send it here.</blockquote>"
        ),
    },
    "create_bot_cancel_hint": {
        "ru": "<b>Вы можете отменить операцию, отправив /cancel</b>",
        "en": "<b>You can cancel the process by sending /cancel</b>",
    },
    "callback_generic_error": {
        "ru": "Произошла ошибка при обработке запроса",
        "en": "An error occurred while processing your request",
    },
    "add_bot_account_banned": {
        "ru": "Ваш аккаунт заблокирован. Обратитесь в техподдержку.",
        "en": "Your account is blocked. Please contact support.",
    },
    "add_bot_token_exists": {
        "ru": "Такой токен уже есть в базе!",
        "en": "This token is already in the database!",
    },
    "add_bot_invalid_api_token": {
        "ru": "Неверный токен. Проверьте и попробуйте снова.",
        "en": "Invalid token. Please check it and try again.",
    },
    "add_bot_success": {
        "ru": (
            "✅ Бот @{username} успешно добавлен!\n"
            "Информация о боте сохранена в базе данных.\n\n"
            "Теперь вы можете использовать этот бот как зеркало основного."
        ),
        "en": (
            "✅ Bot @{username} successfully added!\n"
            "Bot information has been saved to the database.\n\n"
            "You can now use this bot as a mirror of the main bot."
        ),
    },
    "add_bot_webhook_failed": {
        "ru": (
            "⚠️ Бот @{username} авторизован, но не удалось настроить вебхук.\n"
            "Попробуйте снова или обратитесь в поддержку."
        ),
        "en": (
            "⚠️ Bot @{username} was authenticated but webhook setup failed.\n"
            "Please try again or contact support."
        ),
    },
    "add_bot_error": {
        "ru": "❌ Произошла ошибка: {error}",
        "en": "❌ An error occurred: {error}",
    },
    "token_input_cancelled": {
        "ru": "Операция отменена.",
        "en": "Operation cancelled.",
    },
    "token_input_cancel_process": {
        "ru": "Операция добавления бота отменена.",
        "en": "Bot addition process cancelled.",
    },
    "business_unknown_sender": {
        "ru": "Неизвестный отправитель",
        "en": "Unknown sender",
    },
    "business_unknown_user": {
        "ru": "Неизвестный пользователь",
        "en": "Unknown user",
    },
    "business_sender_block": {
        "ru": "<blockquote><b>{label}: {sender}</b></blockquote>\n",
        "en": "<blockquote><b>{label}: {sender}</b></blockquote>\n",
    },
    "business_sender_chat_suffix": {
        "ru": " (чат ID: {chat_id})",
        "en": " (chat ID: {chat_id})",
    },
    "business_label_sender": {
        "ru": "Отправитель",
        "en": "Sender",
    },
    "business_label_text": {
        "ru": "Текст",
        "en": "Text",
    },
    "business_deleted_title": {
        "ru": "<blockquote><i>🗑 Это {item} было удалено:</i></blockquote>\n",
        "en": "<blockquote><i>🗑 This {item} was deleted:</i></blockquote>\n",
    },
    "business_edit_title": {
        "ru": "⚡️изменение сообщения⚡️\n",
        "en": "⚡️Message edit⚡️\n",
    },
    "business_edit_user": {
        "ru": "",
        "en": "",
    },
    "business_edit_chat": {
        "ru": "<blockquote><i>🗂 Чат: {chat}</i></blockquote>\n",
        "en": "<blockquote><i>🗂 Chat: {chat}</i></blockquote>\n",
    },
    "business_edit_was": {
        "ru": "<blockquote><i>📝 Было: {value}</i></blockquote>\n",
        "en": "<blockquote><i>📝 Was: {value}</i></blockquote>\n",
    },
    "business_edit_became": {
        "ru": "<blockquote><i>🔄 Стало: {value}</i></blockquote>\n",
        "en": "<blockquote><i>🔄 Became: {value}</i></blockquote>\n",
    },
    "business_edit_changes": {
        "ru": "<blockquote><i>🔍 Изменения: {value}</i></blockquote>\n",
        "en": "<blockquote><i>🔍 Changes: {value}</i></blockquote>\n",
    },
    "business_edit_previous_missing": {
        "ru": "предыдущая версия не найдена",
        "en": "previous version is missing",
    },
    "subscription_media_not_allowed": {
        "ru": "🚫 На вашем тарифе сохранение исчезающих медиа недоступно. Обновите подписку, чтобы включить эту функцию.",
        "en": "🚫 Your current plan does not allow saving disappearing media. Upgrade to enable this feature.",
    },
    "subscription_media_weekly_limit_reached": {
        "ru": (
            "⚠️ Вы превысили недельный лимит на сохранение исчезающих медиа ({limit}).\n\n"
            "Лимит сбросится {reset}.\n\n"
            "Обновите тариф, чтобы получить больше."
        ),
        "en": (
            "⚠️ You reached the weekly disappearing media quota ({limit}).\n\n"
            "It resets on {reset}.\n\n"
            "Upgrade your plan for more."
        ),
    },
    "subscription_media_monthly_limit_reached": {
        "ru": (
            "⚠️ Вы превысили месячный лимит на сохранение исчезающих медиа ({limit}).\n\n"
            "Обновление лимита произойдет {reset}.\n\n"
            "Для большего лимита обновите подписку."
        ),
        "en": (
            "⚠️ You reached the monthly disappearing media quota ({limit}).\n\n"
            "It refreshes on {reset}.\n\n"
            "Upgrade your subscription for more."
        ),
    },
    "subscription_notification_weekly_limit_reached": {
        "ru": (
            "⚠️ Вы превысили недельный лимит уведомлений ({limit}).\n\n"
            "Следующее обновление лимита {reset}.\n\n"
            "Для расширения возможностей обновите тариф."
        ),
        "en": (
            "⚠️ Weekly notification limit reached ({limit}).\n\n"
            "Quota resets on {reset}.\n\n"
            "Upgrade your plan for extended limits."
        ),
    },
    "subscription_notification_monthly_limit_reached": {
        "ru": (
            "⚠️ Вы превысили месячный лимит уведомлений ({limit}).\n\n"
            "Лимит обновится {reset}.\n\n"
            "Хотите без ограничений — оформите более высокий план."
        ),
        "en": (
            "⚠️ Monthly notification limit reached ({limit}).\n\n"
            "Quota refreshes on {reset}.\n\n"
            "Consider upgrading for unlimited alerts."
        ),
    },
    "subscription_plan_free_details": {
        "ru": (
            "<b>Free — начни без риска</b>\n\n"
            "👾Идеально, чтобы попробовать наш сервис.\n"
            "<blockquote>\n"
            "• Данные не сохраняются — полная приватность.\n"
            "• До 50 уведомлений в месяц о важных изменениях и удалениях.\n"
            "• Просмотр до 3 одноразовых файлов в месяц.\n"
            "</blockquote>\n"
            "Данный тариф бесплатный и доступен всем.\n"
        ),
        "en": (
            "<b>Free — start with zero risk</b>\n\n"
            "👾Perfect for trying our service.\n"
            "<blockquote>\n"
            "• No data is stored — complete privacy.\n"
            "• Up to 50 notifications per month about important changes and deletions.\n"
            "• View up to 3 single-use files per month.\n"
            "</blockquote>\n"
            "This plan is free and available to everyone.\n"
        ),
    },
    "subscription_plan_overview": {
        "ru": "Выберите тариф, чтобы разблокировать сохранение исчезающих медиа:",
        "en": "Choose a plan to unlock disappearing media capture:",
    },
    "subscription_select_period": {
        "ru": "Выберите период подписки для тарифа {plan}:",
        "en": "Choose a billing period for the {plan} plan:",
    },
    "subscription_select_payment": {
        "ru": "Выберите способ оплаты для тарифа {plan} ({period}).",
        "en": "Choose a payment method for the {plan} plan ({period}).",
    },
    "subscription_plan_free": {
        "ru": "Free",
        "en": "Free",
    },
    "subscription_plan_lite": {
        "ru": "Lite",
        "en": "Lite",
    },
    "subscription_plan_pro": {
        "ru": "Pro",
        "en": "Pro",
    },
    "subscription_plan_free_summary": {
        "ru": "Free — начни без риска",
        "en": "Free — start with zero risk",
    },
    "subscription_plan_lite_summary": {
        "ru": "Lite — больше возможностей, минимальная цена",
        "en": "Lite — more features, minimal price",
    },
    "subscription_plan_pro_summary": {
        "ru": "Pro — максимум свободы",
        "en": "Pro — maximum freedom",
    },
    "subscription_plan_lite_details": {
        "ru": (
            "Lite — больше возможностей, минимальная цена\n\n"
            "👾Подходит тем, кому важен регулярный контроль.\n"
            "<blockquote>\n"
            "• Данные хранятся 3 дня — всегда можно вернуться и проверить.\n"
            "• До 500 уведомлений в месяц (или 250 в неделю при недельной подписке).\n"
            "• Просмотр одноразовых медиа: до 10 в неделю или 25 в месяц.\n"
            "</blockquote>\n"
            "Отличный баланс цены и возможностей.\n"
        ),
        "en": (
            "Lite — more features, minimal price\n\n"
            "👾Ideal for those who need regular monitoring.\n"
            "<blockquote>\n"
            "• Data stored for 3 days — revisit and verify anytime.\n"
            "• Up to 500 notifications per month (or 250 weekly with the weekly plan).\n"
            "• Disappearing media access: up to 10 per week or 25 per month.\n"
            "</blockquote>\n"
            "A great balance between price and capability.\n"
        ),
    },
    "subscription_plan_pro_details": {
        "ru": (
            "Pro — максимум свободы\n\n"
            "👾Выбирают те, кому нужны безлимитные уведомления и длительное хранение данных.\n"
            "<blockquote>\n"
            "• Данные хранятся до 1 недели (недельная подписка) или 1 месяца (месячная подписка).\n"
            "• Уведомления без ограничений — всегда вовремя.\n"
            "• Просмотр одноразовых медиа: до 50 в неделю или 150 в месяц.\n"
            "</blockquote>\n"
            "Отличный баланс цены и возможностей.\n"
            "Полный контроль и максимум возможностей.\n"
        ),
        "en": (
            "Pro — maximum freedom\n\n"
            "👾Chosen by those who need unlimited alerts and long-term data retention.\n"
            "<blockquote>\n"
            "• Data stored up to 1 week (weekly plan) or 1 month (monthly plan).\n"
            "• Unlimited notifications — always on time.\n"
            "• Disappearing media access: up to 50 per week or 150 per month.\n"
            "</blockquote>\n"
            "An exceptional price-to-feature balance.\n"
            "Full control and maximum capabilities.\n"
        ),
    },
    "subscription_already_active": {
        "ru": "У вас уже активна подписка до <b>{date}</b>.",
        "en": "You already have an active subscription until <b>{date}</b>.",
    },
    "subscription_already_active_no_expiry": {
        "ru": "У вас уже активна подписка.",
        "en": "You already have an active subscription.",
    },
    "subscription_period_week": {
        "ru": "Неделя",
        "en": "Week",
    },
    "subscription_period_month": {
        "ru": "Месяц",
        "en": "Month",
    },
    "subscription_payment_stars": {
        "ru": "Оплатить {amount} ⭐ через Telegram Stars",
        "en": "Pay {amount} ⭐ via Telegram Stars",
    },
    "subscription_payment_stars_discount": {
        "ru": "Оплатить {amount} ⭐ (со скидкой)",
        "en": "Pay {amount} ⭐ (discount applied)",
    },
    "subscription_payment_crypto_discount": {
        "ru": "Оплатить {amount} {asset} через CryptoBot (со скидкой)",
        "en": "Pay {amount} {asset} via CryptoBot (discount applied)",
    },
    "subscription_payment_crypto": {
        "ru": "Оплатить {amount} {asset} через CryptoBot",
        "en": "Pay {amount} {asset} via CryptoBot",
    },
    "subscription_invoice_sent": {
        "ru": "Счёт отправлен. Завершите оплату, и подписка активируется автоматически.",
        "en": "Invoice sent. Complete the payment and your subscription will activate automatically.",
    },
    "subscription_payment_pending": {
        "ru": "Счёт на оплату отправлен. Оплатите его, чтобы активировать подписку.",
        "en": "Invoice created. Complete the payment to activate your subscription.",
    },
    "subscription_payment_success": {
        "ru": "✅ Подписка <b>{plan}</b> активна до {date}.",
        "en": "✅ <b>{plan}</b> plan is active until {date}.",
    },
    "subscription_payment_success_no_expiry": {
        "ru": "✅ Подписка <b>{plan}</b> активирована.",
        "en": "✅ <b>{plan}</b> plan activated.",
    },
    "subscription_payment_failed": {
        "ru": "❌ Не удалось обработать платёж. Попробуйте ещё раз или свяжитесь с поддержкой.",
        "en": "❌ Payment could not be processed. Try again or contact support.",
    },
    "subscription_upgrade_notice": {
        "ru": "Обновление с Lite: 90% оплаченной суммы учтено.",
        "en": "Upgrade from Lite: 90% of your previous payment was credited.",
    },
    "subscription_upgrade_period_mismatch": {
        "ru": "Обновление доступно только при выборе того же периода (неделя или месяц), что и у вашей активной подписки Lite.",
        "en": "Upgrading is only available when you choose the same period (week or month) as your active Lite plan.",
    },
    "subscription_admin_notification": {
        "ru": "💳 Пользователь {user_id} оплатил тариф {plan} ({period}) через {method}.",
        "en": "💳 User {user_id} purchased {plan} ({period}) via {method}.",
    },
    "subscription_marketing": {
        "ru": (
            "<b>Free — начни без риска</b>\n"
            "Идеально, чтобы попробовать сервис.\n"
            "• Данные не сохраняются — полная приватность.\n"
            "• До 50 уведомлений о важных изменениях и удалениях в месяц.\n"
            "• Просмотр до 3 одноразовых файлов в месяц.\n"
            "⸻\n"
            "<b>Lite — больше возможностей, минимальная цена</b>\n"
            "Для тех, кому важен регулярный контроль без переплат.\n"
            "• Данные хранятся 3 дня — всегда можно вернуться и проверить.\n"
            "• До 1000 уведомлений в месяц (или 250 в неделю при недельной подписке).\n"
            "• Просмотр одноразовых медиа: до 10 в неделю или 25 в месяц.\n"
            "⸻\n"
            "<b>Pro — максимум свободы</b>\n"
            "Подходит тем, кому нужны безлимитные уведомления и длительное хранение.\n"
            "• Данные хранятся до 1 недели (недельная подписка) или 1 месяца (месячная подписка).\n"
            "• Уведомления без ограничений — всегда вовремя.\n"
            "• Просмотр одноразовых медиа: до 50 в неделю или 150 в месяц.\n"
            "Выбирайте подходящий тариф и контролируйте переписку в деталях!"
        ),
        "en": (
            "<b>Free — start with zero risk</b>\n"
            "Perfect for testing the service.\n"
            "• No data storage — complete privacy.\n"
            "• Up to 50 alerts per month about edits and deletions.\n"
            "• Access up to 3 one-time files per month.\n"
            "⸻\n"
            "<b>Lite — more features, small price</b>\n"
            "Great when you need regular insights without overpaying.\n"
            "• Data stored for 3 days — plenty of time to review.\n"
            "• Up to 1,000 alerts per month (or 250 per week with a weekly plan).\n"
            "• One-time media access: up to 10 per week or 25 per month.\n"
            "⸻\n"
            "<b>Pro — maximum freedom</b>\n"
            "Designed for users who need unlimited alerts and extended storage.\n"
            "• Data stored for 1 week (weekly plan) or 1 month (monthly plan).\n"
            "• Unlimited notifications — stay informed at all times.\n"
            "• One-time media access: up to 50 per week or 150 per month.\n"
            "Pick the plan that fits your workflow and stay in control!"
        ),
    },
    "subscription_marketing_plain": {
        "ru": "AsintSave — ваш личный архив Telegram. Бот сохраняет исчезающие фото и видео, фиксирует изменения в личных сообщениях и восстанавливает удалённые сообщения до их исчезновения.",
        "en": "AsintSave — your personal Telegram vault. The bot captures self-destructing photos and videos, tracks edits in private chats, and restores deleted messages before they vanish.",
    },
    "media_saved_caption": {
        "ru": "<b>☝️Сохранено с помощью @{bot_username}</b>",
        "en": "<b>☝️Saved with @{bot_username}</b>",
    },
    "media_error_processing": {
        "ru": "Ошибка: Не удалось обработать {media_type}.",
        "en": "Error: Failed to process {media_type}.",
    },
}

BUTTONS: Dict[str, Dict[str, str]] = {
    "language_ru": {
        "ru": "Русский",
        "en": "Русский",
    },
    "language_en": {
        "ru": "English",
        "en": "English",
    },
    "agreement_link": {
        "ru": "Пользовательское соглашение",
        "en": "User Agreement",
    },
    "agreement_confirm": {
        "ru": "Я прочитал",
        "en": "I have read",
    },
    "settings_change_language": {
        "ru": "Изменить язык",
        "en": "Change language",
    },
    "settings_view_agreement": {
        "ru": "Показать соглашение",
        "en": "View agreement",
    },
    "tutorial": {
        "ru": "❗️Тутор по установке",
        "en": "❗️Setup guide",
    },
    "news": {
        "ru": "📰 Новостной канал",
        "en": "📰 News channel",
    },
    "subscription_open": {
        "ru": "💳 Подписка",
        "en": "💳 Subscription",
    },
    "profile_open": {
        "ru": "👤 Профиль",
        "en": "👤 Profile",
    },
    "subscription_back": {
        "ru": "⬅️ Назад",
        "en": "⬅️ Back",
    },
}

LANGUAGE_LABELS = {
    "ru": {
        "ru": "Русский",
        "en": "Russian",
    },
    "en": {
        "ru": "Английский",
        "en": "English",
    },
}

BUSINESS_ITEM_NAMES = {
    "text": {
        "ru": "сообщение",
        "en": "message",
    },
    "photo": {
        "ru": "фото",
        "en": "photo",
    },
    "video": {
        "ru": "видео",
        "en": "video",
    },
    "video_note": {
        "ru": "видеозаметка",
        "en": "video note",
    },
    "voice": {
        "ru": "голосовое сообщение",
        "en": "voice message",
    },
}

MEDIA_TYPE_LABELS = {
    "photo": {
        "ru": "фото",
        "en": "photo",
    },
    "video": {
        "ru": "видео",
        "en": "video",
    },
    "voice": {
        "ru": "голосовое сообщение",
        "en": "voice message",
    },
    "video_note": {
        "ru": "видеозаметка",
        "en": "video note",
    },
    "text": {
        "ru": "сообщение",
        "en": "message",
    },
}


def get_text(key: str, language: str | None, /, **format_kwargs: str) -> str:
    """Return localized text for the given key and language."""
    lang = (language or DEFAULT_LANGUAGE).lower()
    if key in MESSAGES:
        template = MESSAGES[key].get(lang) or MESSAGES[key][DEFAULT_LANGUAGE]
    else:
        template = key
    return template.format(**format_kwargs)


def get_label(mapping: Dict[str, Dict[str, str]], key: str, language: str | None) -> str:
    """Return localized label from mapping with graceful fallback."""
    lang = (language or DEFAULT_LANGUAGE).lower()
    variants = mapping.get(key, {})
    return variants.get(lang) or variants.get(DEFAULT_LANGUAGE) or key
