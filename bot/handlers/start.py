from aiogram import F, Router, types
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.i18n import gettext as _
from aiogram.utils.chat_action import ChatActionSender
from aiogram.enums import ParseMode

from bot.keyboards.inline.languages import language_keyboard
from bot.services.analytics import analytics
from bot.services.users import set_language_code, get_language_code
from bot.services.gemini import get_gemini_client


class Onboarding(StatesGroup):
    """FSM for onboarding: /start -> choose language -> ask question."""

    choose_language = State()
    ask_question = State()


router = Router(name="start")


@router.message(CommandStart())
@analytics.track_event("Sign Up")
async def start_handler(message: types.Message, state: FSMContext) -> None:
    """Start onboarding and ask user to choose language."""
    await state.set_state(Onboarding.choose_language)
    await message.answer(
        _("Please choose your language:"),
        reply_markup=language_keyboard(),
    )


@router.callback_query(F.data.startswith("set_lang:"), Onboarding.choose_language)
@analytics.track_event("Language Set")
async def language_chosen(callback: types.CallbackQuery, state: FSMContext, session) -> None:
    """Handle language selection and persist it to the database."""
    if not callback.from_user:
        return

    lang_code = callback.data.split(":", 1)[1]
    await set_language_code(session=session, user_id=callback.from_user.id, language_code=lang_code)

    await state.set_state(Onboarding.ask_question)
    await callback.message.edit_reply_markup(reply_markup=None)

    # Build localized prompt without relying on i18n update cycle
    prompts = {
        "en": "Great! Now send your question.",
        "es": "¡Genial! Ahora envía tu pregunta.",
        "pt": "Ótimo! Agora envie sua pergunta.",
        "fr": "Super! Maintenant envoyer votre question.",
        "de": "Großartig! Jetzt sende deine Frage.",
        "zh": "太棒了! 现在请发送您的问题.",
        "ja": "すばらしい！これで、質問を送信できます。",
        "ko": "멋지다! 이제 질문을 보낼 수 있습니다.",
        "ru": "Отлично! Напишите ваш вопрос.",
        "ar": "جيد! الآن أرسل سؤالك.",
    }
    prompt_text = prompts.get(lang_code, prompts["en"])  # fallback to English

    await callback.message.answer(prompt_text)
    await callback.answer()


@router.message(Onboarding.ask_question)
async def question_handler(message: types.Message, state: FSMContext, session) -> None:
    """Handle user's question via Gemini 2.5 Flash-Lite with FAQ context and selected language."""
    if not message.from_user or not message.text:
        return

    user_id = message.from_user.id
    # Determine language preference
    lang_code = await get_language_code(session=session, user_id=user_id) or (message.from_user.language_code or "en")

    # Indicate typing while processing
    async with ChatActionSender.typing(bot=message.bot, chat_id=message.chat.id):
        client = get_gemini_client()
        answer_text = await client.answer(question=message.text, language_code=lang_code)

    if not answer_text:
        fallbacks = {
            "en": "Sorry, I couldn't generate an answer right now. Please try again or rephrase your question.",
            "es": "Lo siento, no puedo generar una respuesta en este momento. Por favor, inténtalo de nuevo o reformula tu pregunta.",
            "pt": "Desculpe, eu não posso gerar uma resposta no momento. Por favor, tente novamente ou reformule sua pergunta.",
            "fr": "Désolé, je ne peux pas générer de réponse pour le moment. Veuillez réessayer ou reformuler votre question.",
            "de": "Es tut uns leid, ich kann keine Antwort generieren. Bitte versuchen Sie es erneut oder reformulieren Sie Ihre Frage.",
            "zh": "对不起，我暂时无法生成回答。请尝试重新提问或重新表述您的问题。",
            "ja": "ごめんなさい。今のところ回答を生成できません。再度試してください。",
            "ko": "죄송합니다, 저는 지금 답변을 생성할 수 없습니다. 다시 시도하거나 질문을 다시 말씀해 주세요.",
            "ru": "Извините, не удалось сгенерировать ответ. Попробуйте еще раз или переформулируйте вопрос.",
            "ar": "عذرًا، لم يمكنني إنشاء إجابة في الوقت الحالي. يرجى المحاولة مرة أخرى أو إعادة الإصلاح الأسئلة.",
        }
        await message.answer(fallbacks.get(lang_code, fallbacks["en"]))
        return

    # Telegram message limit safety
    max_len = 4000
    for i in range(0, len(answer_text), max_len):
        await message.answer(answer_text[i:i + max_len], parse_mode=ParseMode.MARKDOWN)

    # Stay in ask_question state for follow-up questions
    await state.set_state(Onboarding.ask_question)
