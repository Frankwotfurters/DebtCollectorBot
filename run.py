import logging
from telegram.ext import Updater
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, ParseMode
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
from dotenv import load_dotenv
import re
import os

# Logging config
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)

db = DBHelper()
FRIEND, AMOUNT, DESC = range(3)
CALC = 0
WIPE, CONFIRMCLEAR = range(2)
REMOVE, CONFIRMDELETE = range(2)
SETDEFAULT = 0

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

def formatAmount(amount):
    """Formats the amount to start with a + for positive values, or a - for negative values"""
    # Convert to float
    try:
        amount = float(amount)
    except:
        return False

    if amount >= 0:
        # Positive or 0
        return f'+${amount}'

    # Negative
    return f'-${abs(amount)}'

def formatTotal(amount):
    """Formats the total to start with - for negative values, or nothing for positive values"""
    # Convert to float
    try:
        amount = round(float(amount), 2)
    except:
        return False

    if amount >= 0:
        # Positive or 0
        return f'${amount}'

    # Negative
    return f'-${abs(amount)}'

def start(update: Update, context: CallbackContext):
    # Help menu
    res = """
__*Welcome to the Debt Collector Bot\!*__
Here are the available commands:

/start or /help \- Display this menu\.

/add \- Add a new record\. Can also be done in one line\. Example: /add Bob 15 Pizza

/check \- Check existing records and total between you and a friend\.

/clear \- Clear all records between you and a friend\.

/delete \- Delete a specific record\.

/default \- Sets your default friend\. Enables you to use /add without specifying your friend's name\.

/github \- View the open\-source code behind this bot on GitHub\.
    """
    context.bot.send_message(chat_id=update.effective_chat.id, text=res, parse_mode='MarkdownV2')

def github(update: Update, context: CallbackContext):
    # Display github repo
    res = """
    Check out the code behind this bot at https://github.com/Frankwotfurters/DebtCollectorBot
    """
    context.bot.send_message(chat_id=update.effective_chat.id, text=res)

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
            update.message.reply_text(f'Added record: {friend} {formatAmount(amount)}, {desc}')
        elif friend and not amount:
            # Invalid amount given
            update.message.reply_text('Please enter a valid amount!\n' +
                                        'Examples: 4.50, -2, 0.64')
        elif not friend and amount:
            # Default friend is not set
            update.message.reply_text('Please set a default friend to use /add without supplying a name!\n' + 
                                        '/default')
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
        'How much do they owe you?\n' +
        'Or, send /cancel to go back.',
        reply_markup=ReplyKeyboardRemove(),
    )

    return AMOUNT

def amount(update: Update, context: CallbackContext):
    """Stores amount info and ends the conversation."""
    # Retrieve user input
    context.user_data["addAmount"] = update.message.text

    if not isValidAmount(context.user_data["addAmount"]):
        # If invalid input
        # Display error
        update.message.reply_text('Please enter a valid number!')

        # Prompt user for amount input again
        update.message.reply_text('How much do they owe you?')

        # Repeat this function
        return AMOUNT

    # Prompt user for desc input
    update.message.reply_text(
        'Add a short description! (or skip)',
        reply_markup=ReplyKeyboardMarkup(
            [['/skip', '/cancel']], one_time_keyboard=True, input_field_placeholder='Skip?'
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
    update.message.reply_text(f'Added record: {context.user_data["addFriend"]} {formatAmount(context.user_data["addAmount"])}, {context.user_data["addDesc"]}',
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
    db.add_record(update.message.chat_id, context.user_data["addFriend"], context.user_data["addAmount"])

    # Logging
    update.message.reply_text(f'Added record: {context.user_data["addFriend"]} {formatAmount(context.user_data["addAmount"])}')

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
    
    if data:
        # If records exist, build response
        header = [f'{len(data)} record(s) found for {context.user_data["checkFriend"]}:']
        body = [f'{formatAmount(x[0])} {x[1]}' for x in data]
        total = [f'Total: {formatTotal(sum([x[0] for x in data]))}']
        res = '\n'.join(header + body + total)
        
    else:
        # If no records of queried friend
        res = f'No records found for {context.user_data["checkFriend"]}.'

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

    # No records found
    if data is None:
        update.message.reply_text(text=f'You have not added any records!\n' +
                                  'Start with /add.',
                                reply_markup=ReplyKeyboardRemove()
                                )

        # End the conversation
        return ConversationHandler.END

    # Craft response
    header = [f'Recent records:']
    body = [f'{x[0]}) {x[3]} {formatAmount(x[2])} {", " + x[4] if x[4] else ""}' for x in data]
    res = '\n'.join(header + body)

    # Reply with data
    update.message.reply_text(text=res,
                              reply_markup=ReplyKeyboardRemove()
                              )

    # Prepare reply keyboard
    reply_keyboard = [[x.split(')')[0] for x in body]]
    reply_keyboard[0].append('/cancel')

    # Prompt user for ID input
    update.message.reply_text(
        'Choose the ID of the record to delete:',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='ID'
        ),
    )

    return REMOVE

def remove(update: Update, context: CallbackContext):
    """Retrieve user input and display record to be removed"""
    # Retrieve user input
    context.user_data["deleteID"] = update.message.text

    # Get existing record first
    data = db.get_record_by_ID(update.message.chat_id, context.user_data["deleteID"])

    if not data:
        # Record does not exist / not owned by user
        # Prompt user for reply again
        update.message.reply_text('ID not found! Please try again:')

        # Repeat this function
        return REMOVE

    # Prepare reply keyboard
    reply_keyboard = [['Yes', 'No']]

    # Prompt user for confirmation
    update.message.reply_text(
        'Would you like to delete:\n' +
        f'{data[0][0]}) {data[0][3]} {formatAmount(data[0][2])} {", " + data[0][4] if data[0][4] else ""}',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Confirmation'
        ),
    )

    return CONFIRMDELETE

def confirmDelete(update: Update, context: CallbackContext):
    """Retrieve confirmation to delete single record"""
    # Get existing record again
    data = db.get_record_by_ID(update.message.chat_id, context.user_data["deleteID"])

    # Retrieve user input
    confirmDelete = update.message.text

    # Check user's response
    if confirmDelete.lower() == 'yes':
        # Received confirmation to delete record
        db.delete_record(update.message.chat_id, context.user_data["deleteID"])

        # Reply user with the record that was deleted
        update.message.reply_text(text='Deleted record:\n' +
                                f'{data[0][0]}) {data[0][3]} {formatAmount(data[0][2])} {", " + data[0][4] if data[0][4] else ""}',
                                reply_markup=ReplyKeyboardRemove()
                                )

        # Clear cache
        del context.user_data["deleteID"]

        return ConversationHandler.END

    else:
        # Anything else will cancel the deletion
        update.message.reply_text(text='Cancelled deletion.',
                                reply_markup=ReplyKeyboardRemove()
                                )

        # Clear cache
        del context.user_data["deleteID"]

        return ConversationHandler.END

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

    # Check for records
    data = db.check_records(update.message.chat_id, context.user_data["clearFriend"])

    # Build response
    header = [f'You are deleting:']
    body = [f'{formatAmount(x[0])} {x[1]}' for x in data]
    res = '\n'.join(header + body)

    # Save total amount
    context.user_data["clearTotal"] = (sum([x[0] for x in data]), len(data))

    # Send user deleted records
    update.message.reply_text(text=res,
                            reply_markup=ReplyKeyboardRemove()
                            )

    # Prepare reply keyboard
    reply_keyboard = [['Yes', 'No']]    

    # Prompt user for confirmation
    update.message.reply_text(
        f'Would you like to clear all records between you and {context.user_data["clearFriend"]}?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Confirmation'
        ),
    )


    return CONFIRMCLEAR

def confirmClear(update: Update, context: CallbackContext):
    """Retrieve confirmation to wipe records of friend"""
    # Retrieve user input
    confirmClear = update.message.text

    # Check user's response
    if confirmClear.lower() == 'yes':
        # Delete from database
        db.clear_record(update.message.chat_id, context.user_data["clearFriend"])

        records = context.user_data["clearTotal"][1]

        if records > 1:
            # Multiple transactions
            res = f'Cleared {formatTotal(context.user_data["clearTotal"][0])} of debt ({records} transactions) from {context.user_data["clearFriend"]}.'
        else:
            # 0-1 transaction
            res = f'Cleared {formatTotal(context.user_data["clearTotal"][0])} of debt ({records} transaction) from {context.user_data["clearFriend"]}.'

        # Reply with data
        update.message.reply_text(text=res,
                                reply_markup=ReplyKeyboardRemove()
                                )

        # Clear cache
        del context.user_data["clearFriend"]
        del context.user_data["clearTotal"]

        return ConversationHandler.END

    else:
        # Anything else will cancel the operation
        update.message.reply_text(text='Cancelled clearing of records.',
                                reply_markup=ReplyKeyboardRemove()
                                )

        # Clear cache
        del context.user_data["clearFriend"]

        return ConversationHandler.END

def default(update: Update, context: CallbackContext):
    """Start conversation to set default friend"""
    # Retrieve current default friend
    currentDefault = db.check_default(update.message.chat_id)

    # Retrieve possible friends
    reply_keyboard = [db.check_friends(update.message.chat_id)]
    
    # Check if default is set
    if currentDefault:
        # Already previously set
        res = f'Your current default friend is *{currentDefault[0][0]}*\.'
        reply_keyboard[0].append('/remove')
    else:
        # Not set
        res = "Your default friend is not set\."

    # Add cancel option
    reply_keyboard[0].append('/cancel')

    # Prompt user for friend input
    update.message.reply_text(
        f'{res} Choose one of the following \(or enter a new name\) to be set as your default friend:',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Who?'
        ),
        parse_mode='MarkdownV2'
    )

    return SETDEFAULT

def setDefault(update: Update, context: CallbackContext):
    """Retrieve user input and set default friend"""
    # Retrieve user input
    context.user_data["defaultFriend"] = update.message.text

    # Send to database
    db.set_default(update.message.chat_id, context.user_data["defaultFriend"])

    # Reply user
    update.message.reply_text(
        f'Your default friend is now *{context.user_data["defaultFriend"]}*\.',
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='MarkdownV2'
    )

    return ConversationHandler.END

def removeDefault(update: Update, context: CallbackContext):
    """Deletes default friend record"""
    # Send to database
    db.delete_default(update.message.chat_id)

    # Reply user
    update.message.reply_text(
        'Removed your default friend.',
        reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END    

def cancel(update: Update, context: CallbackContext):
    """Cancels and ends the conversation."""
    user = update.message.from_user
    logging.info("User %s canceled the conversation.", user.first_name)

    # Get cache entries
    cache = [x for x in context.user_data]

    # Clear cache
    for x in cache:
        del context.user_data[x]

    update.message.reply_text(
        'Cancelled request.', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END

def unknown(update: Update, context: CallbackContext):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")

def main():
    """Run the bot"""
    # Perform first time setup of database
    db.setup()
    
    # Load env file and retrive bot token and port
    load_dotenv('.env')
    TOKEN = os.getenv('BOT_TOKEN')
    PORT = os.getenv('BOT_PORT')
    
    # Initialize telegram bot updater and dispatcher
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Command handlers
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    help_handler = CommandHandler('help', start)
    dispatcher.add_handler(help_handler)

    github_handler = CommandHandler('github', github)
    dispatcher.add_handler(github_handler)

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
            WIPE: [MessageHandler(Filters.text & (~ Filters.command), wipe)],
            CONFIRMCLEAR: [MessageHandler(Filters.text & (~ Filters.command), confirmClear)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(clearConv)

    # Conversation Handler for deleting a single record
    deleteConv = ConversationHandler(
        entry_points=[CommandHandler('delete', delete)],
        states={
            REMOVE: [MessageHandler(Filters.text & (~ Filters.command), remove)],
            CONFIRMDELETE: [MessageHandler(Filters.text & (~ Filters.command), confirmDelete)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(deleteConv)

    # Conversation Handler for setting default friend
    defaultConv = ConversationHandler(
        entry_points=[CommandHandler('default', default)],
        states={
            SETDEFAULT: [MessageHandler(Filters.text & (~ Filters.command), setDefault)]
        },
        fallbacks=[CommandHandler('remove', removeDefault), CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(defaultConv)

    # Handler for unknown commands
    unknown_handler = MessageHandler(Filters.command, unknown)
    dispatcher.add_handler(unknown_handler)

    # Start the bot and wait for response
    updater.start_webhook(listen="0.0.0.0",
                            port=int(PORT),
                            url_path=TOKEN,
                            webhook_url = 'https://vast-waters-99826.herokuapp.com/' + TOKEN)
    updater.idle()
    
if __name__ == "__main__":
    main()