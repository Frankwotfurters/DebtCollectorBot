import logging
from telegram.ext import Updater
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CallbackContext
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, Filters
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)
from dbhelper import DBHelper

# Logging config
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

def start(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text="ayo wasshup man")

def add(update: Update, context: CallbackContext):
    """Start conversation to add a new record"""
    # Retrieve possible friends
    reply_keyboard = [db.check_friends(update.message.chat_id)]

    # Add cancel option
    reply_keyboard[0].append('/cancel')

    # Prompt user for friend input
    update.message.reply_text(
        'Who owes you money? Choose below or type a new name (case insensitive)!',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Who?'
        ),
    )
    
    return FRIEND

def friend(update: Update, context: CallbackContext):
    """Retrive the selected friend and asks for amount input."""
    # Retrieve user input
    context.user_data["addFriend"] = update.message.text

    # Prompt user for amount input
    update.message.reply_text(
        'How much do they owe you?',
        reply_markup=ReplyKeyboardRemove(),
    )

    return AMOUNT

def amount(update: Update, context: CallbackContext):
    """Stores amount info and ends the conversation."""
    # Retrieve user input
    context.user_data["addAmount"] = update.message.text

    # Prompt user for desc input
    update.message.reply_text(
        'Add a short description! (or skip)',
        reply_markup=ReplyKeyboardMarkup(
            [['/skip']], one_time_keyboard=True, input_field_placeholder='Skip?'
        ),
    )

    return DESC

def desc(update: Update, context: CallbackContext):
    """Stores amount info and ends the conversation."""
    # Retrieve user input
    context.user_data["addDesc"] = update.message.text

    # Send to database
    db.add_record(update.message.chat_id, context.user_data["addAmount"], context.user_data["addFriend"], context.user_data["addDesc"])

    # Logging and remove on-screen keyboard
    update.message.reply_text(f'Added record: {context.user_data["addFriend"]} +{context.user_data["addAmount"]}, {context.user_data["addDesc"]}',
                              reply_markup=ReplyKeyboardRemove()
                              )

    # Clear data
    del context.user_data["addFriend"]
    del context.user_data["addAmount"]

    return ConversationHandler.END

def skipDesc(update: Update, context: CallbackContext):
    """Sends data to database without a description"""
    # Retrieve user input
    context.user_data["addDesc"] = update.message.text

    # Send to database
    db.add_record(update.message.chat_id, context.user_data["addAmount"], context.user_data["addFriend"])

    # Logging
    update.message.reply_text(f'Added record: {context.user_data["addFriend"]} +{context.user_data["addAmount"]}')

    # Clear data
    del context.user_data["addFriend"]
    del context.user_data["addAmount"]

    return ConversationHandler.END

def check(update: Update, context: CallbackContext):
    """Start conversation to add a new record"""
    # Retrieve possible friends
    reply_keyboard = [db.check_friends(update.message.chat_id)]

    # Add cancel option
    reply_keyboard[0].append('/cancel')

    # Prompt user for friend input
    update.message.reply_text(
        'Check records for who?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Who?'
        ),
    )

    return CALC


def calc(update: Update, context: CallbackContext):
    """Calculate tabulations of user for selected friend"""
    # Retrieve user input
    context.user_data["checkFriend"] = update.message.text

    # Query database
    data = db.check_records(update.message.chat_id, context.user_data["checkFriend"])

    # Build response
    header = [f'Records for {context.user_data["checkFriend"]}:']
    body = [f'{x[0]} {x[1]}' for x in data]
    total = [f'Total: ${sum([x[0] for x in data])}']
    res = '\n'.join(header + body + total)

    # Reply with data
    context.bot.send_message(chat_id=update.effective_chat.id, text=res)

    return ConversationHandler.END
    
def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logging.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'Bye! I hope we can talk again some day.', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

def unknown(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")

db = DBHelper()

updater = Updater(token='2120538784:AAG7yn55iR4rpvK6J1Lm_E6cv7KvBK0wV7E', use_context=True)
dispatcher = updater.dispatcher

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)

# Conversation Handler for adding records
FRIEND, AMOUNT, DESC = range(3)
addConv = ConversationHandler(
    entry_points=[CommandHandler('add', add)],
    states={
        FRIEND: [MessageHandler(Filters.text & (~ Filters.command), friend)],
        AMOUNT: [MessageHandler(Filters.text & (~ Filters.command), amount)],
        DESC: [MessageHandler(Filters.text & (~ Filters.command), desc)]
    },
    fallbacks=[CommandHandler('skip', skipDesc), CommandHandler('cancel', cancel)],
)
dispatcher.add_handler(addConv)

# Conversation Handler for checking records
CALC = 0
checkConv = ConversationHandler(
    entry_points=[CommandHandler('check', check)],
    states={
        CALC: [MessageHandler(Filters.text & (~ Filters.command), calc)]
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)
dispatcher.add_handler(checkConv)

# Handler for unknown commands
unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(unknown_handler)

db.setup()

updater.start_polling()
updater.idle()