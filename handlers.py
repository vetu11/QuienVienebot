"""
Here should be declared all functions that handle the supported Telegram API calls.
"""

import const
from uuid import uuid4
from bot_tokens import PAYMENT_PROVIDER_TOKEN
from list_manager import list_manager
from list import List
from user_manager import user_manager
from database import database
from lang import get_lang
from telegram import ParseMode, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, InlineQueryResultArticle,\
    InputTextMessageContent


def _create_list_message(list, lang) -> str:
    conn = database.get_connection()

    text = "*%s*" % list.title

    for vote_option in list.vote_options:
        sql = "SELECT full_name FROM users WHERE id IN " \
              "(SELECT user_id FROM user_votes WHERE list_id=? AND vote=? ORDER BY vote_timestamp LIMIT ?)"
        cur = conn.conn.execute(sql, [list.id, vote_option, const.NAMES_PER_VOTE_TYPE])

        text += "\n\n" + lang.get_text("vote_%s_message_line" % vote_option)

        for name in cur.fetchall():
            text += "\n" + name

    return text


def _create_list_keyboard(list, lang, uuid=None) -> list:
    conn = database.get_connection()
    keyboard = [[]]
    option_votes = []
    
    # In some cases, we haven't created the list yet, so we need to use an id to a to be created list.
    if uuid:
        list_id = uuid
    else:
        list_id = list.id

    for vote_option in list.vote_options:
        cur = conn.conn.execute("SELECT count(*) FROM user_votes WHERE list_id=? AND vote=?", [list_id, vote_option])
        option_votes.append((vote_option, cur.fetchone()))

        keyboard[0].append(InlineKeyboardButton(lang.get_text("vote_%s_keyboard" % vote_option,
                                                              callback_data="vote*%s*%s" % (vote_option, list_id))))

    if max(option_votes) > const.NAMES_PER_VOTE_TYPE:
        new_row = []

        link = "t.me/%s?start=%s" % (const.aux.BOT_USERNAME, list_id)

        for votes in option_votes:
            new_row.append(InlineKeyboardButton("(%s)" % votes[1], url=link + "_%s" % votes[0]))

        keyboard.append(new_row)

    new_row = [InlineKeyboardButton(lang.get_text("forward_list"), switch_inline_query="id*%s" % list_id)]
    keyboard.append(new_row)

    return keyboard


def generic_message(bot, update, text_code, **kwargs):
    """Answers the message with a fixed text. Add kwargs to insert text."""
    message = update.effective_message
    lang = get_lang(update.effective_user.language_code)

    message.reply_text(lang.get_text(text_code, **kwargs), parse_mode=ParseMode.MARKDOWN)


def start(bot, update):
    generic_message(bot, update, "start")


def help(bot, update):
    generic_message(bot, update, "help")


def more(bot, update):
    generic_message(bot, update, "more")


def about(bot, update):
    generic_message(bot, update, "about", **{"botusername": bot.username, "version": const.VERSION})


def ping(bot, update):
    update.effective_message.reply_text("Pong!", quote=False)


def donate(bot, update, user_data):
    if PAYMENT_PROVIDER_TOKEN is None:
        generic_message(bot, update, "donations_not_available")
        return

    lang = get_lang(update.effective_user.language_code)

    user_data["donation"] = 5
    text = lang.get_text("donate")
    keyboard = [[InlineKeyboardButton("❤ %s€ ❤" % user_data["donation"], callback_data="donate")],
                [InlineKeyboardButton("⏬", callback_data="don*LLL"),
                 InlineKeyboardButton("⬇️", callback_data="don*LL"),
                 InlineKeyboardButton("🔽", callback_data="don*L"),
                 InlineKeyboardButton("🔼", callback_data="don*G"),
                 InlineKeyboardButton("⬆️", callback_data="don*GG"),
                 InlineKeyboardButton("⏫", callback_data="don*GGG")]]
    update.message.reply_text(text,
                              reply_markup=InlineKeyboardMarkup(keyboard),
                              parse_mode=ParseMode.MARKDOWN,
                              disable_web_page_preview=True)


def change_donation_quantity(bot, update, user_data):

    if "donation" not in user_data:
        user_data["donation"] = 5

    s = update.callback_query.data.split("*")
    change = 5 ** (s[1].count("G") - 1) if "G" in s[1] else -(5 ** (s[1].count("L") - 1))
    user_data["donation"] += change
    if user_data["donation"] < 1:
        user_data["donation"] = 1

    keyboard = [[InlineKeyboardButton("❤ %s€ ❤" % user_data["donation"], callback_data="donate")],
                [InlineKeyboardButton("⏬", callback_data="don*LLL"),
                 InlineKeyboardButton("⬇️", callback_data="don*LL"),
                 InlineKeyboardButton("🔽", callback_data="don*L"),
                 InlineKeyboardButton("🔼", callback_data="don*G"),
                 InlineKeyboardButton("⬆️", callback_data="don*GG"),
                 InlineKeyboardButton("⏫", callback_data="don*GGG")]]

    update.effective_message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(keyboard))
    update.callback_query.answer()


def send_donation_receipt(bot, update, user_data):
    lang = get_lang(update.effective_user.language_code)

    if "donation" not in user_data:
        user_data["donation"] = 5

    title = lang.get_text("donation_title")
    description = lang.get_text("donation_description")
    prices = [LabeledPrice(title, user_data["donation"] * 100)]

    bot.send_invoice(chat_id=update.effective_chat.id,
                     title=title,
                     description=description,
                     payload="approve_donation",
                     provider_token=PAYMENT_PROVIDER_TOKEN,
                     start_parameter="donacion",
                     currency="EUR",
                     prices=prices)
    update.effective_message.edit_reply_markup(reply_markup=InlineKeyboardMarkup([[]]))


def approve_transaction(bot, update):
    query = update.pre_checkout_query

    if query.invoice_payload != 'approve_donation':
        bot.answer_pre_checkout_query(pre_checkout_query_id=query.id, ok=False,
                                      error_message="Algo ha fallado, vuelve a intentarlo por favor.")
    else:
        bot.answer_pre_checkout_query(pre_checkout_query_id=query.id, ok=True)


def completed_donation(bot, update):
    update.effective_message.reply_text("Muchisimas gracias por donar!! ❤️❤️❤️")
    bot.send_message(const.ADMIN_TELEGRAM_ID, "%s ha donado!" % update.effective_user)


def support(bot, update):
    message = update.effective_message
    lang = get_lang(update.effective_user.language_code)

    if len(message.text.replace("/support", "")) > 0:
        message.forward(const.ADMIN_TELEGRAM_ID)
        message.reply_text(lang.get_text("support_sent"))
    else:
        message.reply_text(lang.get_text("support_default"))


def support_group(bot, update):
    generic_message(bot, update, "private_command")


def error(bot, update, error):
    bot.send_message(const.ADMIN_TELEGRAM_ID, "The update:\n%s\nhas caused this error:\n%s" % (str(update), str(error)))


# INLINE QUERIES

def empty_query(bot, update):
    user = user_manager.get_user(update.effective_user)
    user_lists = list_manager.get_lists_from_user(user.id)
    lang = get_lang(user.language_code)
    results = []

    if user_lists:
        for list in user_lists:
            message, keyboard = _create_list_message(list, lang), _create_list_keyboard(list, lang)
            new_result = InlineQueryResultArticle(id=list.id,
                                                  title=list.title,
                                                  description=lang.get_text("send_existent"),
                                                  reply_markup=InlineKeyboardMarkup(keyboard),
                                                  input_message_content=InputTextMessageContent(
                                                      message_text=message,
                                                      parse_mode=ParseMode.MARKDOWN,
                                                      disable_web_page_preview=True))
            results.append(new_result)
    else:
        message = lang.get_text("no_existent_meeting_message", bot_username=const.aux.BOT_USERNAME)

        results = [InlineQueryResultArticle(id="no_meeting",
                                            title=lang.get_text("no_existent_meeting_query_title"),
                                            description=lang.get_text("no_existent_meeting_query_description"),
                                            input_message_content=InputTextMessageContent(
                                                message_text=message,
                                                parse_mode=ParseMode.MARKDOWN,
                                                disable_web_page_preview=True))]

    update.inline_query.answer(results,
                               is_personal=True,
                               cache_time=const.QUERY_CACHE_TIME,
                               switch_pm_text=lang.get_text("donations_accepted"),
                               switch_pm_parameter="donation")


def full_query(bot, update):
    query_split = update.inline_query.query.split("*")
    user = user_manager.get_user(update.effective_user)
    lang = get_lang(user.language_code)

    # If the query starts with id* this is a list search by id.
    if query_split[0] == "id":
        list_id = query_split[1]
        list = list_manager.get_list_by_id(list_id)
        
        if list:
            message, keyboard = _create_list_message(list, lang), _create_list_keyboard(list, lang)
    
            results = [InlineQueryResultArticle(id=list.id,
                                                title=list.id,
                                                description=lang.get_text("send_existent_meeting_query_description"),
                                                reply_markup=InlineKeyboardMarkup(keyboard),
                                                input_message_content=InputTextMessageContent(
                                                    message_text=message,
                                                    parse_mode=ParseMode.MARKDOWN,
                                                    disable_web_page_preview=True)
                                                )]
        else:
            message = lang.get_text("list_not_found_message")

            results = [InlineQueryResultArticle(id="not_found",
                                                title=lang.get_text("list_not_found_query_title"),
                                                description=lang.get_text("list_not_found_query_description"),
                                                input_message_content=InputTextMessageContent(
                                                    message_text=message,
                                                    parse_mode=ParseMode.MARKDOWN,
                                                    disable_web_page_preview=True
                                                ))]

    else:
        list_id = uuid4()
        keyboard = _create_list_keyboard(List, lang, list_id)

        results = [InlineQueryResultArticle(id=list_id,
                                            title=update.inline_query.query,
                                            description=lang.get_text("press_to_send"),
                                            reply_markup=InlineKeyboardMarkup(keyboard),
                                            input_message_content=InputTextMessageContent(
                                                message_text="*%s*" % update.inline_query.query,
                                                parse_mode=ParseMode.MARKDOWN,
                                                disable_web_page_preview=True
                                            ))]

    update.inline_query.answer(results,
                               is_personal=True,
                               cache_time=const.QUERY_CACHE_TIME,
                               switch_pm_text=lang.get_text("donations_accepted"),
                               switch_pm_parameter="donation")


def chosen_result(bot, update):

    # it can't be an empty query, and it can't be a search
    if update.chosen_inline_result.query and "id*" not in update.chosen_inline_result.query:

        List(id=update.chosen_inline_result.result_id,
             from_user_id=update.chosen_inline_result.from_user.id,
             title=update.chosen_inline_result.query)


def cast_vote(bot, update):
    user = user_manager.get_user(update.effective_user)
    lang = get_lang(user.language_code)
    vote, list_id = update.callback_query.data.split("*")[1:2]
    list = list_manager.get_list_by_id(list_id)

    if list:
        conn = database.get_connection()

        # Check if the user has voted before this list
        cur = conn.conn.execute("SELECT * FROM user_votes WHERE user_id=? AND list_id=?", [user.id, list.id])
        if cur.fetchone():
            conn.conn.execute("UPDATE user_votes SET vote=? WHERE user_id=? AND list_id=?", [vote, user.id, list.id])
        else:
            conn.conn.execute("INSERT INTO user_votes VALUES (?, ?, ?)", [user.id, list.id, vote])

        conn.conn.commit()

        message, keyboard = _create_list_message(list, lang), _create_list_keyboard(list, lang)

        bot.edit_message_text(text=message,
                              parse_mode=ParseMode.MARKDOWN,
                              disable_web_page_preview=True,
                              reply_markup=keyboard,
                              inline_message_id=update.callback_query.inline_message_id)
        update.callback_query.answer("okay 👍")
    else:
        update.callback_query.answer(lang.get_text("warning_list_does_not_exist"), shot_alert=True)
        bot.edit_message_reply_markup(inline_message_id=update.callback_query.inline_message_id,
                                      reply_markup=InlineKeyboardMarkup([[]]))
