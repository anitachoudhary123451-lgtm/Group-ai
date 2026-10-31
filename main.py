import os
import io
from PIL import Image
import open_nsfw2 as nsfw
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# Render से सिर्फ Bot Token उठाएगा (AI key की अब कोई जरूरत नहीं है!)
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")

# 18+ शब्दों की लिस्ट (टेक्स्ट के लिए)
BAD_WORDS = ["badword1", "badword2", "adultword"] 

async def filter_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or not update.effective_chat or update.effective_chat.type not in ["group", "supergroup"]:
        return

    # 1. टेक्स्ट मैसेज चेक करने के लिए
    if message.text:
        text = message.text.lower()
        if any(word in text for word in BAD_WORDS):
            try:
                await message.delete()
                return
            except Exception as e:
                print(f"Error deleting text: {e}")

    # 2. फोटो चेक करने के लिए (यह AI सिर्फ फोटो और गिफ्स पर काम करता है)
    if message.photo:
        try:
            # सबसे बड़ी साइज वाली फोटो सिलेक्ट करें
            media_file = await message.photo[-1].get_file()

            # फोटो को सीधे रैम (BytesIO) में डाउनलोड करें
            file_bytes = io.BytesIO()
            await media_file.download_to_memory(out=file_bytes)
            file_bytes.seek(0)

            # PIL Image में बदलें
            image = Image.open(file_bytes)

            # AI मॉडल से फोटो की जांच करें (यह 0.0 से 1.0 के बीच स्कोर देता है)
            nsfw_probability = nsfw.predict_image(image)

            # अगर 18+ होने की संभावना 0.6 (60%) से ज्यादा है तो डिलीट करें
            if nsfw_probability > 0.6:
                try:
                    await message.delete()
                    print(f"Deleted NSFW image. Score: {nsfw_probability}")
                except Exception as e:
                    print(f"Error deleting NSFW image: {e}")

        except Exception as e:
            print(f"Error checking media: {e}")

def main():
    # बॉट शुरू करें
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # टेक्स्ट और फोटो मैसेजेस को मॉनिटर करें
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, filter_messages))
    
    print("100% फ्री AI बॉट चालू हो गया है...")
    app.run_polling()

if __name__ == '__main__':
    main()
