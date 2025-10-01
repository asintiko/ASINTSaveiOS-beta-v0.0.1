from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_panel_kb() -> InlineKeyboardMarkup:
    """Main admin panel keyboard."""
    rows = [
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="⭐️ Выдать подписку", callback_data="admin_subscribe")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🚫 Бан / Разбан", callback_data="admin_manage")],
        [InlineKeyboardButton(text="❌ Закрыть", callback_data="admin_close")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_panel_kb() -> InlineKeyboardMarkup:
    """Keyboard with a button to return to the main panel."""
    rows = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def subscription_plan_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="Lite", callback_data="admin_subscribe_plan:lite")],
        [InlineKeyboardButton(text="Pro", callback_data="admin_subscribe_plan:pro")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_subscribe_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def subscription_period_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="Неделя", callback_data="admin_subscribe_period:week")],
        [InlineKeyboardButton(text="Месяц", callback_data="admin_subscribe_period:month")],
        [InlineKeyboardButton(text="Навсегда", callback_data="admin_subscribe_period:forever")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_subscribe_back_plan")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_subscribe_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def subscription_confirm_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data="admin_subscribe_confirm")],
        [InlineKeyboardButton(text="⬅️ Изменить", callback_data="admin_subscribe_back_period")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_subscribe_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
