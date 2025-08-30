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
from bot.core.config import settings
from aiogram.utils.keyboard import InlineKeyboardBuilder
from bot.cache.redis import set_redis_value
from bot.core.loader import redis_client


class Onboarding(StatesGroup):
    """FSM for onboarding: /start -> choose language -> ask question."""

    choose_language = State()
    ask_question = State()
    ask_support_question = State()


router = Router(name="start")


@router.message(CommandStart())
@analytics.track_event("Sign Up")
async def start_handler(message: types.Message, state: FSMContext) -> None:
    """Start onboarding and ask user to choose language."""
    await state.set_state(Onboarding.choose_language)
    # Reset per-session counters
    await state.update_data(post_start_count=0)
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

    # Increase counter of messages after /start
    data = await state.get_data()
    msg_count: int = int(data.get("post_start_count", 0)) + 1
    await state.update_data(post_start_count=msg_count)

    # Prepare optional support prompt on the 3rd message
    add_support_prompt = msg_count == 3
    support_prompts = {
        "en": ("You can contact technical support directly if your issue remains.", "Contact support", "Please write your question:"),
        "ru": ("Вы можете связаться напрямую с техподдержкой, если проблема не решена.", "Связаться с техподдержкой", "Напишите ваш вопрос:"),
        "es": ("Puede contactar con soporte técnico directamente si su problema persiste.", "Contactar con soporte", "Por favor, escriba su pregunta:"),
        "pt": ("Você pode contatar o suporte técnico diretamente se o problema persistir.", "Contactar o suporte", "Por favor, escreva sua pergunta:"),
        "fr": ("Vous pouvez contacter le support technique directement si votre problème persiste.", "Contacter le support", "Veuillez écrire votre question :"),
        "de": ("Sie können den technischen Support direkt kontaktieren, wenn Ihr Problem weiterhin besteht.", "Support kontaktieren", "Bitte schreiben Sie Ihre Frage:"),
        "zh": ("如果您的问题仍未解决，您可以直接联系技术支持。", "联系技术支持", "请写下您的问题："),
        "ja": ("問題が解決しない場合は、技術サポートに直接連絡できます。", "サポートに連絡する", "質問を書いてください:"),
        "ko": ("문제가 해결되지 않은 경우 기술 지원에 직접 문의할 수 있습니다.", "지원팀에 문의", "질문을 작성해 주세요:"),
        "ar": ("إذا لم تُحل مشكلتك، يمكنك التواصل مباشرة مع الدعم الفني.", "التواصل مع الدعم", "يرجى كتابة سؤالك:"),
    }
    prompt_text, button_text, ask_text = support_prompts.get(lang_code, support_prompts.get("en"))

    # Telegram message limit safety, append support prompt to the last chunk when needed
    max_len = 4000
    total_len = len(answer_text)
    for i in range(0, total_len, max_len):
        is_last = (i + max_len) >= total_len
        chunk = answer_text[i:i + max_len]

        reply_markup = None
        if add_support_prompt and is_last:
            chunk = f"{chunk}\n\n{prompt_text}"
            kb = InlineKeyboardBuilder()
            kb.button(text=button_text, callback_data="contact_support")
            reply_markup = kb.as_markup()

        await message.answer(chunk, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)

    # Stay in ask_question state for follow-up questions
    await state.set_state(Onboarding.ask_question)


@router.callback_query(F.data == "contact_support")
async def contact_support_clicked(callback: types.CallbackQuery, state: FSMContext) -> None:
    """User clicked contact support: remove button and ask to write a question."""
    if not callback.from_user:
        return

    # Remove the inline button from the original message
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    # Determine language preference from FSM or user
    data = await state.get_data()
    lang_code = data.get("language_code") or (callback.from_user.language_code or "en")
    support_prompts = {
        "en": "Please write your question:",
        "ru": "Напишите ваш вопрос:",
        "es": "Por favor, escriba su pregunta:",
        "pt": "Por favor, escreva sua pergunta:",
        "fr": "Veuillez écrire votre question :",
        "de": "Bitte schreiben Sie Ihre Frage:",
        "zh": "请写下您的问题：",
        "ja": "質問を書いてください:",
        "ko": "질문을 작성해 주세요:",
        "ar": "يرجى كتابة سؤالك:",
    }
    ask_text = support_prompts.get(lang_code, support_prompts["en"])

    await state.set_state(Onboarding.ask_support_question)
    await callback.message.answer(ask_text)
    await callback.answer()


@router.message(Onboarding.ask_support_question)
async def forward_support_question(message: types.Message, state: FSMContext) -> None:
    """Forward user's support question to managers group and stay in ask_question state."""
    if not message.from_user or not message.text:
        return

    group_id = settings.MANAGERS_GROUP_ID
    if not group_id:
        await message.answer("Support is not configured. Please try again later.")
        await state.set_state(Onboarding.ask_question)
        return

    username = f"@{message.from_user.username}" if message.from_user.username else f"ID:{message.from_user.id}"
    text_to_group = (
        f"Вопрос от пользователя {username} (ID: {message.from_user.id}):\n\n{message.text}"
    )

    # Inline button 'Ответить' (always Russian)
    kb = InlineKeyboardBuilder()
    kb.button(text="Ответить", callback_data=f"support_reply:{message.from_user.id}")

    await message.bot.send_message(chat_id=group_id, text=text_to_group, reply_markup=kb.as_markup())

    # Return to ask_question state for further AI Q&A
    await state.set_state(Onboarding.ask_question)


@router.callback_query(F.data.startswith("support_reply:"))
async def support_reply_clicked(callback: types.CallbackQuery) -> None:
    """Manager clicked 'Ответить' in the managers group; remember to route their next message."""
    if not callback.from_user:
        return

    if callback.message and callback.message.chat and settings.MANAGERS_GROUP_ID:
        if int(callback.message.chat.id) != int(settings.MANAGERS_GROUP_ID):
            await callback.answer()
            return

    try:
        _, user_id_str = callback.data.split(":", 1)
        target_user_id = int(user_id_str)
    except Exception:
        await callback.answer()
        return

    # Save mapping manager_id -> user_id with TTL
    key = f"support_reply_wait:{callback.from_user.id}"
    await set_redis_value(key=key, value=str(target_user_id), ttl=900)

    await callback.answer("Напишите ответ пользователю в этом чате.", show_alert=False)


@router.message(F.chat.id == settings.MANAGERS_GROUP_ID)
async def handle_manager_group_message(message: types.Message) -> None:
    """Route the next message from the manager who clicked 'Ответить' to the user, text only."""
    if not message.from_user:
        return

    # Check pending mapping for this manager
    key = f"support_reply_wait:{message.from_user.id}"
    pending = await redis_client.get(key)
    if not pending:
        return

    try:
        target_user_id = int(pending.decode() if isinstance(pending, (bytes, bytearray)) else pending)
    except Exception:
        await redis_client.delete(key)
        return

    # Only relay text content to the user to hide the manager account
    text = message.text or message.caption
    if not text:
        return

    try:
        await message.bot.send_message(chat_id=target_user_id, text=text)
    finally:
        await redis_client.delete(key)
