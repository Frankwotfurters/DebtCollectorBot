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
import re

# Logging config
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

db = DBHelper()
FRIEND, AMOUNT, DESC = range(3)
CALC = 0
WIPE = 0

def isValidName(name):
    """Check if name is suitable"""
    # Uses regex to check for suitable name
    # Name must be a single word without any numbers or special characters
    return bool(re.match('^[^\d\W]+$', name))

def isValidAmount(amount):
    """Check if amount is suitable to put into the database"""
    # Uses regex to test for suitable amount
    # Accepts: 12.04, +12.04, -12.04, .5, 0
    # Rejects: '12.', '.'
    return bool(re.match('^[-|+]?(0|[1-9]\d*)?(\.\d+)?(?<=\d)$', amount))

def start(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text="ayo wasshup man")

def quickAdd(chat_id, args):
    """Add new record without starting conversation
    Example: /add Ryan 12 Pizza"""
    # Check if first argument includes a name
    if isValidName(args[0]):
        friend = args[0]

        # Retrieve and validate amount
        if isValidAmount(args[1]):
            amount = args[1]

            # Retrieve and check for desc
            if len(args) > 2:
                # Desc is the remaining words
                desc = " ".join(args[2:])
            else:
                # No desc given
                desc = ""

            # Send to database
            db.add_record(chat_id, args[0], args[1], desc)

            return friend, amount, desc

        else:
            # If invalid amount
            return friend, None, None
            
    elif isValidAmount(args[0]):
        # If first argument isn't a name,
        # Check if next argument is the amount
        amount = args[0]

        # Retrieve default friend
        result = db.check_default(chat_id)

        logging.info(result)

        # Check if a default friend is set
        if not result:
            # Not set
            return None, amount, None
        else:
            # Got default friend
            friend = result[0][0]

        # Check for desc
        if len(args) > 1:
            # Desc is the remaining words
            desc = " ".join(args[1:])
        else:
            # No desc given
            desc = ""
            
        # Send to database
        db.add_record(chat_id, friend, args[0], desc)

        return friend, amount, desc

    else:
        # Unknown command
        return None, None, None

def add(update: Update, context: CallbackContext):
    """Start conversation to add a new record"""
    # If user gave arguments with the command (for quickAdd):
    if context.args:
        friend, amount, desc = quickAdd(update.message.chat_id, context.args)

        # Check if command is successful
        if friend and amount:
            # If successfully added record
            update.message.reply_text(f'Added record: {friend} +{amount}, {desc}')
        elif friend and not amount:
            # Invalid amount given
            update.message.reply_text('Please enter a valid amount!\n' +
                                        'Examples: 4.50, -2, 0.64')
        elif not friend and amount:
            # Default friend is not set
            update.message.reply_text('Please set a default friend to use /add without supplying a name!\n' + 
                                        '/settings')
        else:
            # Incorrect usage
            update.message.reply_text(f'Usage of quick /add:\n' +
                                        '\t/add [name](optional) [amount] [description](optional)\n' +
                                        'Examples:\n' +
                                        '\t/add Ryan 8.70 Starbucks\n' +
                                        '\t/add 2 Iced Tea\n' +
                                        '\t/add 5')

        return ConversationHandler.END
    
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

    # Ensure name is valid
    if not isValidName(context.user_data["addFriend"]):
        # If invalid name
        context.bot.send_message(chat_id=update.effective_chat.id, text='Name must be a single word without any numbers or special characters! Please try again.')

        # Repeat this function
        return FRIEND

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
    db.add_record(update.message.chat_id, context.user_data["addFriend"], context.user_data["addAmount"], context.user_data["addDesc"])

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
    update.message.reply_text(text=res,
                              reply_markup=ReplyKeyboardRemove()
                              )

    # Clear cache
    del context.user_data["checkFriend"]

    return ConversationHandler.END

def delete(update: Update, context: CallbackContext):
    """Start conversation to delete a single existing record"""
    # Retrieve recent records
    data = db.check_recent(update.message.chat_id)

    header = [f'Recent records:']
    body = [f'[{x[0]}]: {x[3]} {x[2]} {", " + x[4] if x[4] else ""}' for x in data]
    res = '\n'.join(header + body)

    # Reply with data
    update.message.reply_text(text=res,
                              reply_markup=ReplyKeyboardRemove()
                              )

    # # Prompt user for friend input
    # update.message.reply_text(
    #     'Clear records for who?',
    #     reply_markup=ReplyKeyboardMarkup(
    #         reply_keyboard, one_time_keyboard=True, input_field_placeholder='Who?'
    #     ),
    # )

    return WIPE
def clear(update: Update, context: CallbackContext):
    """Start conversation to clear existing records for a friend"""
    # Retrieve possible friends
    reply_keyboard = [db.check_friends(update.message.chat_id)]

    # Add cancel option
    reply_keyboard[0].append('/cancel')

    # Prompt user for friend input
    update.message.reply_text(
        'Clear records for who?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Who?'
        ),
    )

    return WIPE

def wipe(update: Update, context: CallbackContext):
    """Retrieve user input and wipe records of friend"""
    # Retrieve user input
    context.user_data["clearFriend"] = update.message.text

    # Get existing records first
    data = db.check_records(update.message.chat_id, context.user_data["clearFriend"])

    # Delete from database
    db.delete_record(update.message.chat_id, context.user_data["clearFriend"])
    logging.info(data)

    # Build response
    total = sum([x[0] for x in data])
    res = f'Cleared ${total} of debt ({len(data)} transactions) from {context.user_data["clearFriend"]}'

    # Reply with data
    update.message.reply_text(text=res,
                              reply_markup=ReplyKeyboardRemove()
                              )

    return ConversationHandler.END
    
def cancel(update: Update, context: CallbackContext):
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logging.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text(
        'Bye! I hope we can talk again some day.', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

def unknown(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")

def main():
    """Run the bot"""
    # Perform first time setup of database
    db.setup()

    updater = Updater(token='***REMOVED***', use_context=True)
    dispatcher = updater.dispatcher

    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    start_handler = CommandHandler('delete', delete)
    dispatcher.add_handler(start_handler)

    # Conversation Handler for adding records
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
    checkConv = ConversationHandler(
        entry_points=[CommandHandler('check', check)],
        states={
            CALC: [MessageHandler(Filters.text & (~ Filters.command), calc)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(checkConv)

    # Conversation Handler for clearing records
    clearConv = ConversationHandler(
        entry_points=[CommandHandler('clear', clear)],
        states={
            WIPE: [MessageHandler(Filters.text & (~ Filters.command), wipe)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(clearConv)

    # Handler for unknown commands
    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)

    # Start the bot and wait for response
    updater.start_polling()
    updater.idle()
    
if __name__ == "__main__":
    main()