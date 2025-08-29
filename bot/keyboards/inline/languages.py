from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.i18n import gettext as _
from aiogram.utils.keyboard import InlineKeyboardBuilder


def language_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard for choosing language."""
    buttons = [
        [
            InlineKeyboardButton(text="ES 🇪🇸", callback_data="set_lang:es"),
            InlineKeyboardButton(text="FR 🇫🇷", callback_data="set_lang:fr"),
            InlineKeyboardButton(text="DE 🇩🇪", callback_data="set_lang:de"),
            
            
        ],
        [
            InlineKeyboardButton(text="PT 🇵🇹", callback_data="set_lang:pt"),
            InlineKeyboardButton(text="RU 🇷🇺", callback_data="set_lang:ru"),
            InlineKeyboardButton(text="AR 🇸🇦", callback_data="set_lang:ar"),
            

        ],
        [
            InlineKeyboardButton(text="KO 🇰🇷", callback_data="set_lang:ko"),
            InlineKeyboardButton(text="ZH 🇨🇳", callback_data="set_lang:zh"),
            InlineKeyboardButton(text="JA 🇯🇵", callback_data="set_lang:ja"),
        ],
        [  
            InlineKeyboardButton(text="EN 🇬🇧", callback_data="set_lang:en"),
        ],
    ]

    keyboard = InlineKeyboardBuilder(markup=buttons)
    keyboard.adjust(3)
    return keyboard.as_markup()

InlineKeyboardButton(text="AR 🇸🇦", callback_data="set_lang:ar"),
