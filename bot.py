import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import openai
import os
from dotenv import load_dotenv
import pandas as pd

load_dotenv()

# Initialize Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Replace with your tokens and API keys
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

# Predefined keyword dataset
keyword_data = pd.read_csv("keywords_dataset.csv")  # Add a pre-prepared CSV with keywords per industry

# States for conversation flow
INDUSTRY, BUSINESS_OBJ, WEBSITE, SOCIAL_MEDIA, PPC, AUDIENCE, LOCATION, QUESTION = range(8)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome to the Digital Marketing Assistant Bot! Let's analyze your business data.")
    await update.message.reply_text("What industry is your business in?")
    return INDUSTRY

async def ask_business_obj(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['industry'] = update.message.text
    await update.message.reply_text("What is your business objective? (e.g., lead generation, sales, etc.)")
    return BUSINESS_OBJ

async def ask_website(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['business_objective'] = update.message.text
    await update.message.reply_text("Do you have a website? If yes, please provide the URL.")
    return WEBSITE

async def ask_social_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['website'] = update.message.text
    await update.message.reply_text("Do you have any social media platforms? If yes, please provide the URL.")
    return SOCIAL_MEDIA

async def ask_ppc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['social_media'] = update.message.text
    await update.message.reply_text("Do you use PPC campaigns? (Yes/No)")
    return PPC

async def ask_audience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ppc'] = update.message.text
    await update.message.reply_text("Who are you trying to reach? (e.g., young adults, professionals)")
    return AUDIENCE

async def ask_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['audience'] = update.message.text
    await update.message.reply_text("What location would you like to target?")
    return LOCATION

async def generate_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['location'] = update.message.text
    industry = context.user_data['industry'].lower()
    relevant_keywords = keyword_data[keyword_data['industry'].str.lower() == industry]['keywords'].values
    keyword_response = ", ".join(relevant_keywords) if len(relevant_keywords) > 0 else "No predefined keywords found."
    await update.message.reply_text(f"Here are relevant keywords for your industry: {keyword_response}")
    await update.message.reply_text("You can now ask me any digital marketing question!")
    return QUESTION

async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_question = update.message.text
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=f"Answer this digital marketing question in detail: {user_question}",
        max_tokens=300
    )
    await update.message.reply_text(response['choices'][0]['text'])
    await update.message.reply_text("Would you like to ask something else? (Type 'exit' to quit)")
    return QUESTION

async def exit_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Thank you for using the bot! Have a great day!")
    return ConversationHandler.END

def fetch_ppc_trends():
    URL = "https://databox.com/ppc-industry-benchmarks"
    response = requests.get(URL)
    soup = BeautifulSoup(response.content, 'html.parser')
    ppc_trends = {}
    table = soup.find("table")
    for row in table.find_all("tr")[1:]:
        cols = row.find_all("td")
        industry = cols[0].text.strip()
        cpc = cols[1].text.strip()
        ppc_trends[industry] = cpc
    return ppc_trends

async def ppc_trends_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    trends = fetch_ppc_trends()
    message = "\n".join([f"{industry}: {cpc}" for industry, cpc in trends.items()])
    await update.message.reply_text(f"Latest PPC Trends:\n{message}")

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            INDUSTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_business_obj)],
            BUSINESS_OBJ: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_website)],
            WEBSITE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_social_media)],
            SOCIAL_MEDIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_ppc)],
            PPC: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_audience)],
            AUDIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_location)],
            LOCATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_keywords)],
            QUESTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question),
                MessageHandler(filters.Regex("(?i)^exit$"), exit_conversation)
            ],
        },
        fallbacks=[CommandHandler('exit', exit_conversation)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('ppc_trends', ppc_trends_command))

    application.run_polling()

if __name__ == "__main__":
    main()
