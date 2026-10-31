import os, io, threading, numpy as np, cv2, tempfile
from PIL import Image
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from opennsfw2 import make_open_nsfw_model

# --- 1. RENDER FAKE PORT (Timed Out fix) ---
class Handler(BaseHTTPRequestHandler):
    def do_GET(self): 
        self.send_response(200); self.end_headers(); self.wfile.write(b"BOT RUNNING")
def run_fake_server():
    port = int(os.environ.get("PORT", 10000))
    HTTPServer(('0.0.0.0', port), Handler).serve_forever()
threading.Thread(target=run_fake_server, daemon=True).start()

# --- 2. AI MODEL LOAD (Ek baar hi load hoga) ---
print("Loading Powerful AI...")
nsfw_model = make_open_nsfw_model()
print("AI Loaded! Ready to Delete.")

BOT_TOKEN = os.environ.get("BOT_TOKEN")
# Thoda bhi ganda lage to delete -> 0.35 kar diya
NSFW_THRESHOLD = 0.35 

def predict_score(pil_image):
    try:
        img = pil_image.convert("RGB").resize((256, 256))
        arr = np.array(img) / 255.0
        arr = np.expand_dims(arr, axis=0)
        score = float(nsfw_model.predict(arr)[0][0])
        return score
    except: return 0.0

def check_video_file(file_path):
    """Video/GIF ka beech ka frame nikal ke check karega"""
    try:
        cap = cv2.VideoCapture(file_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames == 0: return 0.0
        # Beech ka frame lo
        cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames // 2)
        ret, frame = cap.read()
        cap.release()
        if not ret: return 0.0
        # CV2 (BGR) -> PIL (RGB)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame)
        return predict_score(pil_img)
    except Exception as e:
        print(f"Video check error: {e}")
        return 0.0

async def filter_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    if not message or not update.effective_chat: return

    try:
        score = 0
        file_obj = None
        is_video_type = False

        if message.photo:
            file_obj = await message.photo[-1].get_file()
        elif message.animation: # GIF
            file_obj = await message.animation.get_file()
            is_video_type = True
        elif message.video:
            file_obj = await message.video.get_file()
            is_video_type = True
        elif message.document:
            file_obj = await message.document.get_file()
            if message.document.mime_type and "video" in message.document.mime_type:
                is_video_type = True

        if not file_obj:
            return

        # Temp file me download karo
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            await file_obj.download_to_drive(tmp.name)
            
            if is_video_type:
                score = check_video_file(tmp.name)
            else:
                # Photo ke liye direct
                image = Image.open(tmp.name)
                score = predict_score(image)
            
            os.unlink(tmp.name) # File delete karo

        print(f"File checked | Type: {'Video/GIF' if is_video_type else 'Photo'} | Score: {score}")

        if score > NSFW_THRESHOLD:
            try:
                await message.delete()
                print(f"✅ DELETED! Score {score} > {NSFW_THRESHOLD}")
            except Exception as e:
                print(f"Delete failed (Bot Admin nahi hai kya?): {e}")

    except Exception as e:
        print(f"Main Error: {e}")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.Document.ALL, filter_messages))
    print(f"Powerful Bot Started! Threshold: {NSFW_THRESHOLD}")
    app.run_polling()

if __name__ == '__main__':
    main()
