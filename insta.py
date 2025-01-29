import os
import instaloader
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler

# Conversation states
ASK_USERNAME, ASK_PASSWORD, ASK_2FA, ASK_FOLLOWER_USERNAME, ASK_NEXT_ACTION = range(5)

# Temporary storage for user credentials and follower's username
user_data = {}

# Command handler for /start
def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Welcome! Please enter your Instagram username:")
    return ASK_USERNAME

# Handler for receiving the Instagram username
def ask_username(update: Update, context: CallbackContext) -> int:
    user_data['username'] = update.message.text
    update.message.reply_text("Please enter your Instagram password:")
    return ASK_PASSWORD

# Handler for receiving the Instagram password
def ask_password(update: Update, context: CallbackContext) -> int:
    user_data['password'] = update.message.text
    update.message.reply_text("Logging in to Instagram...")

    # Try logging in to Instagram with Instaloader
    L = instaloader.Instaloader()

    try:
        L.login(user_data['username'], user_data['password'])
        update.message.reply_text("Logged in successfully!")
        update.message.reply_text("Please enter the Instagram username of the follower or following person whose posts you want to scrape:")
        user_data['L'] = L  # Store the Instaloader object for further use
        return ASK_FOLLOWER_USERNAME

    except instaloader.exceptions.TwoFactorAuthRequiredException:
        update.message.reply_text("Two-factor authentication is required. Please enter the 2FA code:")
        user_data['L'] = L  # Store the Instaloader object for further use
        return ASK_2FA

    except Exception as e:
        update.message.reply_text(f"Error logging in: {e}")
        return ConversationHandler.END

# Handler for receiving the 2FA code
def ask_2fa(update: Update, context: CallbackContext) -> int:
    two_factor_code = update.message.text
    L = user_data.get('L')

    try:
        L.two_factor_login(two_factor_code)
        update.message.reply_text("Logged in with 2FA successfully!")
        update.message.reply_text("Please enter the Instagram username of the follower or following person whose posts you want to scrape:")
        return ASK_FOLLOWER_USERNAME

    except Exception as e:
        update.message.reply_text(f"Error logging in with 2FA: {e}")
        return ConversationHandler.END

# Handler for receiving the follower's username and scraping posts
def ask_follower_username(update: Update, context: CallbackContext) -> int:
    follower_username = update.message.text
    user_data['follower_username'] = follower_username

    update.message.reply_text(f"Scraping posts, stories, highlights, reels, and tagged posts from {follower_username}...")
    return scrape_all(update, context, user_data['L'])

# Function to create a sub-folder
def create_sub_folder(parent_folder, sub_folder_name):
    folder_path = os.path.join(parent_folder, sub_folder_name)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path

# Function to scrape Instagram data and save media locally in organized folders
def scrape_all(update: Update, context: CallbackContext, L: instaloader.Instaloader) -> int:
    follower_username = user_data['follower_username']  # The username of the follower or following person to scrape

    try:
        # Load the profile of the follower or following person
        profile = instaloader.Profile.from_username(L.context, follower_username)
        update.message.reply_text(f"Downloading posts, stories, highlights, reels, and tagged posts from {follower_username}...")

        # Create a main folder for the follower
        main_folder = f"{follower_username}_data"
        if not os.path.exists(main_folder):
            os.makedirs(main_folder)

        # 1. Download posts (including photos, reels, and videos) to a separate folder
        posts_folder = create_sub_folder(main_folder, 'posts')
        for post in profile.get_posts():
            L.download_post(post, target=posts_folder)

        # 2. Download stories to a separate folder
        try:
            stories_folder = create_sub_folder(main_folder, 'stories')
            stories = L.get_stories(userids=[profile.userid])
            for story in stories:
                for item in story.get_items():
                    L.download_storyitem(item, target=stories_folder)
            update.message.reply_text(f"Stories from {follower_username} downloaded.")
        except Exception as e:
            update.message.reply_text(f"Error downloading stories: {e}")

        # 3. Download highlights to a separate folder
        try:
            highlights_folder = create_sub_folder(main_folder, 'highlights')
            highlights = L.get_highlights(user=profile)
            for highlight in highlights:
                for item in highlight.get_items():
                    L.download_storyitem(item, target=highlights_folder)
            update.message.reply_text(f"Highlights from {follower_username} downloaded.")
        except Exception as e:
            update.message.reply_text(f"Error downloading highlights: {e}")

        # 4. Download tagged posts to a separate folder
        try:
            tagged_posts_folder = create_sub_folder(main_folder, 'tagged_posts')
            for post in profile.get_tagged_posts():
                L.download_post(post, target=tagged_posts_folder)
            update.message.reply_text(f"Tagged posts from {follower_username} downloaded.")
        except Exception as e:
            update.message.reply_text(f"Error downloading tagged posts: {e}")

        update.message.reply_text(f"Scraping completed. Data saved locally in the '{main_folder}' folder.")

        # After completion, ask user if they want to scrape more or logout
        update.message.reply_text("Do you want to scrape more data from another follower? Reply with 'yes' to scrape another or 'logout' to end the session.")
        return ASK_NEXT_ACTION

    except Exception as e:
        update.message.reply_text(f"An error occurred while scraping: {e}")
        return ConversationHandler.END

# Handler to ask the user if they want to scrape more data or logout
def ask_next_action(update: Update, context: CallbackContext) -> int:
    response = update.message.text.lower()

    if response == 'yes':
        update.message.reply_text("Please enter the Instagram username of the follower or following person whose posts you want to scrape:")
        return ASK_FOLLOWER_USERNAME
    elif response == 'logout':
        update.message.reply_text("Logging out. Thank you for using the bot!")
        return logout(update, context)
    else:
        update.message.reply_text("Invalid response. Please reply with 'yes' to scrape more data or 'logout' to end the session.")
        return ASK_NEXT_ACTION

# Function to handle logout and end the session
def logout(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("You have been logged out successfully. Goodbye!")
    return ConversationHandler.END

# Cancel conversation
def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Canceled.')
    return ConversationHandler.END

def main() -> None:
    # Telegram bot token
    TELEGRAM_TOKEN = 'Your-telegram-bot-token'

    # Create Updater and Dispatcher
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Conversation handler to handle the user flow
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASK_USERNAME: [MessageHandler(Filters.text & ~Filters.command, ask_username)],
            ASK_PASSWORD: [MessageHandler(Filters.text & ~Filters.command, ask_password)],
            ASK_2FA: [MessageHandler(Filters.text & ~Filters.command, ask_2fa)],
            ASK_FOLLOWER_USERNAME: [MessageHandler(Filters.text & ~Filters.command, ask_follower_username)],
            ASK_NEXT_ACTION: [MessageHandler(Filters.text & ~Filters.command, ask_next_action)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    # Add the conversation handler to the dispatcher
    dispatcher.add_handler(conv_handler)

    # Start the bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
