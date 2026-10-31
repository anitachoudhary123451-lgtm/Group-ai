import os
import io
import threading
import numpy as np
from PIL import Image
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from opennsfw2 import make_open_nsfw_model

# --- RENDER KE LIYE FAKE PORT (Isse Timed Out error khatam hoga) ---
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running - AI Model Loaded")

def run_fake_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), Handler)
    print(f"Fake server started on port {port}")
    server.serve_forever()

threading.Thread(target=run_fake_server, daemon=True).start()
# -------------------------------------------------------------------

print("AI Model loading...")
nsfw_model = make_open_nsfw_model()
print("AI Model loaded!")

BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")
BAD_WORDS = ["badword1", "badword2", "adultword"] 

def predict_nsfw(pil_image):
    try:
        img = pil_image.convert("RGB").resize((256, 256))
        img_array = np.array(img) / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        score = nsfw_model.predict(img_array)[0][0]
        return score
    except Exception as e:
        print(f"Predict error: {e}")
        return 0.0

async def filter_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or not update.effective_chat or update.effective_chat.type not in ["group", "supergroup"]:
        return
    if message.text:
        text = message.text.lower()
        if any(word in text for word in BAD_WORDS):
            try:
                await message.delete()
                return
            except Exception as e:
                print(f"Error deleting text: {e}")
    if message.photo:
        try:
            media_file = await message.photo[-1].get_file()
            file_bytes = io.BytesIO()
            await media_file.download_to_memory(out=file_bytes)
            file_bytes.seek(0)
            image = Image.open(file_bytes)
            nsfw_probability = predict_nsfw(image)
            if nsfw_probability > 0.6:
                try:
                    await message.delete()
                    print(f"Deleted NSFW image. Score: {nsfw_probability}")
                except Exception as e:
                    print(f"Error deleting NSFW image: {e}")
        except Exception as e:
            print(f"Error checking media: {e}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, filter_messages))
    print("100% Free AI Bot chalu ho gaya hai...")
    app.run_polling()

if __name__ == '__main__':
    main()
