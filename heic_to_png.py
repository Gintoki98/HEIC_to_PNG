import os
import zipfile
import shutil
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from PIL import Image
import pillow_heif

# Telegram API credentials
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
STRING_SESSION = os.getenv('STRING_SESSION')  # Replace with your actual session string

# Set up the bot using StringSession
bot = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Folder setup
DOWNLOAD_DIR = "downloads"
OUTPUT_DIR = "converted"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def extract_zip(zip_path, extract_to):
    """Extracts a ZIP file."""
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(extract_to)

async def convert_heic_to_png(input_folder, output_folder):
    """Converts all .HEIC images in a folder to .PNG."""
    os.makedirs(output_folder, exist_ok=True)

    for file in os.listdir(input_folder):
        if file.lower().endswith(".heic"):
            input_path = os.path.join(input_folder, file)
            output_path = os.path.join(output_folder, f"{os.path.splitext(file)[0]}.png")

            heif_image = pillow_heif.open_heif(input_path)
            image = Image.frombytes(heif_image.mode, heif_image.size, heif_image.data)
            image.save(output_path, "PNG")

async def create_zip(folder_path, zip_name):
    """Creates a ZIP file from a folder."""
    zip_path = f"{zip_name}.zip"
    shutil.make_archive(zip_name, 'zip', folder_path)
    return zip_path

async def split_zip(zip_path, max_size_mb=2000):
    """Splits a ZIP file into smaller parts if it exceeds max_size_mb."""
    max_size = max_size_mb * 1024 * 1024  # Convert MB to bytes
    parts = []
    
    if os.path.getsize(zip_path) > max_size:
        part_num = 1
        with open(zip_path, "rb") as src_file:
            while chunk := src_file.read(max_size):
                part_name = f"{zip_path[:-4]}_part{part_num}.zip"
                with open(part_name, "wb") as part_file:
                    part_file.write(chunk)
                parts.append(part_name)
                part_num += 1
        os.remove(zip_path)  # Remove the original oversized ZIP
    else:
        parts.append(zip_path)
    
    return parts

@bot.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply("Send me a .zip file containing HEIC images, and I'll convert them to PNG!")

@bot.on(events.NewMessage)
async def handle_file(event):
    """Handles incoming ZIP files, processes them, and sends back the PNG ZIP."""
    if event.file and event.file.name.endswith(".zip"):
        await event.reply("Downloading ZIP file...")
        zip_path = os.path.join(DOWNLOAD_DIR, event.file.name)

        # Download ZIP file
        await event.download_media(zip_path)
        await bot.send_message(event.chat_id, "ZIP downloaded, processing...")

        extract_folder = os.path.join(DOWNLOAD_DIR, "extracted")
        converted_folder = os.path.join(OUTPUT_DIR, "converted_png")

        # Extract, convert, and create ZIP
        await extract_zip(zip_path, extract_folder)
        await convert_heic_to_png(extract_folder, converted_folder)
        zip_output_path = await create_zip(converted_folder, "converted_images")
        await bot.send_message(event.chat_id, "Images converted, checking file size...")

        # Split ZIP if necessary
        zip_parts = await split_zip(zip_output_path)

        # Send converted ZIP parts
        for part in zip_parts:
            await bot.send_message(event.chat_id, f"Uploading {os.path.basename(part)}...")
            await event.reply(file=part)
            os.remove(part)  # Remove each part after sending

        # Cleanup
        os.remove(zip_path)
        shutil.rmtree(extract_folder)
        shutil.rmtree(converted_folder)

# Start bot
print("Bot is running...")
bot.run_until_disconnected()
