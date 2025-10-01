from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.localization import AGREEMENT_URLS, BUTTONS, DEFAULT_LANGUAGE, TUTORIAL_URLS


def _resolve_language(language: str | None) -> str:
    return (language or DEFAULT_LANGUAGE).lower()


def tut_kb(language: str | None) -> InlineKeyboardMarkup:
    lang = _resolve_language(language)
    tutorial_url = TUTORIAL_URLS.get(lang, TUTORIAL_URLS[DEFAULT_LANGUAGE])
    tutorial = InlineKeyboardButton(
        text=BUTTONS["tutorial"].get(lang, BUTTONS["tutorial"][DEFAULT_LANGUAGE]),
        url=tutorial_url,
    )
    profile = InlineKeyboardButton(
        text=BUTTONS["profile_open"].get(lang, BUTTONS["profile_open"][DEFAULT_LANGUAGE]),
        callback_data="profile:view",
    )
    subscribe = InlineKeyboardButton(
        text=BUTTONS["subscription_open"].get(lang, BUTTONS["subscription_open"][DEFAULT_LANGUAGE]),
        callback_data="subscription:menu",
    )
    channel = InlineKeyboardButton(
        text=BUTTONS["news"].get(lang, BUTTONS["news"][DEFAULT_LANGUAGE]),
        url="https://t.me/ASINTSave",
    )
    rows = [[tutorial], [profile], [subscribe], [channel]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def language_selection_keyboard() -> InlineKeyboardMarkup:
    rows = [[
        InlineKeyboardButton(text=BUTTONS["language_ru"][DEFAULT_LANGUAGE], callback_data="lang:ru"),
        InlineKeyboardButton(text=BUTTONS["language_en"][DEFAULT_LANGUAGE], callback_data="lang:en"),
    ]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def agreement_keyboard(language: str | None) -> InlineKeyboardMarkup:
    lang = _resolve_language(language)
    url = AGREEMENT_URLS.get(lang, AGREEMENT_URLS[DEFAULT_LANGUAGE])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BUTTONS["agreement_link"].get(lang, BUTTONS["agreement_link"][DEFAULT_LANGUAGE]), url=url)],
            [InlineKeyboardButton(text=BUTTONS["agreement_confirm"].get(lang, BUTTONS["agreement_confirm"][DEFAULT_LANGUAGE]), callback_data="agreement:accept")],
        ]
    )


def settings_keyboard(language: str | None) -> InlineKeyboardMarkup:
    lang = _resolve_language(language)
    url = AGREEMENT_URLS.get(lang, AGREEMENT_URLS[DEFAULT_LANGUAGE])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=BUTTONS["settings_change_language"].get(lang, BUTTONS["settings_change_language"][DEFAULT_LANGUAGE]), callback_data="settings:change_language")],
            [InlineKeyboardButton(text=BUTTONS["settings_view_agreement"].get(lang, BUTTONS["settings_view_agreement"][DEFAULT_LANGUAGE]), url=url)],
        ]
    )
