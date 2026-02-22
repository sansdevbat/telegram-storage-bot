import os
import logging
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, CallbackQueryHandler
)
from telegram.constants import ParseMode

from config import BOT_TOKEN, GROUP_ID, ADMIN_IDS, GROUP_LINK, MAX_FILE_SIZE
from database import Database

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize database
db = Database()

class StorageBot:
    def __init__(self):
        self.bot_username = None
        self.group_id = int(GROUP_ID) if GROUP_ID else None
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command handler"""
        user = update.effective_user
        
        # Welcome message
        welcome_text = f"""
🌟 **Welcome to Storage Bot!** 🌟

Hello {user.first_name}! 

📁 **Yeh bot aapki files ko store karta hai**
• Group mein file bhejen → Auto-save
• Har file ka unique link milega
• Link share karen → File download

**Kaise use karein:**
1️⃣ Pehle humare group mein join karein: {GROUP_LINK}
2️⃣ Group mein file upload karein
3️⃣ Bot aapko file ka link dega
4️⃣ Link kisi ko bhi bhejen

**Commands:**
/myfiles - Apni uploaded files
/search - Files search karein
/stats - Bot statistics
/help - Help menu

🚀 **Start using now!**
        """
        
        # Create keyboard
        keyboard = [
            [InlineKeyboardButton("📢 Join Group", url=GROUP_LINK)],
            [InlineKeyboardButton("📁 My Files", callback_data="myfiles")],
            [InlineKeyboardButton("🔍 Search", callback_data="search")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def handle_group_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle messages in group"""
        # Check if message is in the correct group
        if str(update.effective_chat.id) != str(self.group_id):
            return
        
        # Check if message has media
        if not (update.message.document or update.message.video or 
                update.message.photo or update.message.audio or 
                update.message.voice):
            return
        
        user = update.effective_user
        message = update.message
        
        # Process file
        file_info = await self.process_file(message, user)
        
        if file_info:
            # Generate custom link
            custom_link = db.generate_custom_link(file_info['file_id'])
            
            # Create share button
            bot_username = context.bot.username
            file_url = f"https://t.me/{bot_username}?start={custom_link}"
            
            # Success message
            success_text = f"""
✅ **File Saved Successfully!**

📌 **File Name:** `{file_info['file_name']}`
📊 **Size:** {self.format_size(file_info['file_size'])}
🔗 **Share Link:**

`{file_url}`

📱 **Use buttons below:**
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("📋 Copy Link", callback_data=f"copy_{custom_link}"),
                    InlineKeyboardButton("📥 Download", callback_data=f"get_{custom_link}")
                ],
                [InlineKeyboardButton("📁 My Files", callback_data="myfiles")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await message.reply_text(
                success_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=reply_markup
            )
    
    async def process_file(self, message, user):
        """Process and save file to database"""
        try:
            # Get file info based on type
            if message.document:
                file_id = message.document.file_id
                file_name = message.document.file_name
                file_size = message.document.file_size
                mime_type = message.document.mime_type
                file_unique_id = message.document.file_unique_id
                file_type = 'document'
            elif message.video:
                file_id = message.video.file_id
                file_name = message.video.file_name or f"video_{message.video.file_unique_id}.mp4"
                file_size = message.video.file_size
                mime_type = 'video/mp4'
                file_unique_id = message.video.file_unique_id
                file_type = 'video'
            elif message.photo:
                # Get largest photo
                photo = message.photo[-1]
                file_id = photo.file_id
                file_name = f"photo_{photo.file_unique_id}.jpg"
                file_size = photo.file_size
                mime_type = 'image/jpeg'
                file_unique_id = photo.file_unique_id
                file_type = 'photo'
            elif message.audio:
                file_id = message.audio.file_id
                file_name = message.audio.file_name or f"audio_{message.audio.file_unique_id}.mp3"
                file_size = message.audio.file_size
                mime_type = message.audio.mime_type or 'audio/mpeg'
                file_unique_id = message.audio.file_unique_id
                file_type = 'audio'
            else:
                return None
            
            # Check file size
            if file_size > MAX_FILE_SIZE * 1024 * 1024:
                await message.reply_text(f"❌ File size limit: {MAX_FILE_SIZE}MB")
                return None
            
            # Get caption
            caption = message.caption or ""
            
            # Save to database
            success = db.add_file(
                file_id=file_id,
                file_name=file_name,
                file_size=file_size,
                mime_type=mime_type,
                caption=caption,
                uploaded_by=user.id,
                file_unique_id=file_unique_id,
                message_id=message.message_id,
                file_type=file_type
            )
            
            if success:
                return {
                    'file_id': file_id,
                    'file_name': file_name,
                    'file_size': file_size,
                    'file_type': file_type
                }
            else:
                await message.reply_text("⚠️ File already exists in database!")
                return None
                
        except Exception as e:
            logger.error(f"Error processing file: {e}")
            await message.reply_text("❌ Error processing file!")
            return None
    
    async def handle_private_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle private messages"""
        message = update.message
        text = message.text
        
        # Check if it's a link access
        if text and text.startswith('/start '):
            custom_link = text.split(' ')[1]
            await self.send_file_by_link(update, context, custom_link)
            return
        
        # Handle search query
        if text and text.startswith('/search'):
            query = text.replace('/search', '').strip()
            if query:
                await self.search_files(update, context, query)
            else:
                await message.reply_text("🔍 Search query bhejen:\n`/search filename`", parse_mode=ParseMode.MARKDOWN)
    
    async def send_file_by_link(self, update: Update, context: ContextTypes.DEFAULT_TYPE, custom_link):
        """Send file using custom link"""
        # Get file from database
        file_info = db.get_file_by_custom_link(custom_link)
        
        if not file_info:
            await update.message.reply_text("❌ File not found or link invalid!")
            return
        
        # Increment download count
        db.increment_download_count(file_info[1])  # file_id
        
        # Send file
        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action="upload_document"
            )
            
            # Send based on file type
            file_id = file_info[1]  # file_id column
            
            if file_info[10] == 'photo':  # file_type
                await update.message.reply_photo(
                    photo=file_id,
                    caption=f"📁 {file_info[2]}\n📥 Downloads: {file_info[5]}"
                )
            elif file_info[10] == 'video':
                await update.message.reply_video(
                    video=file_id,
                    caption=f"📁 {file_info[2]}\n📥 Downloads: {file_info[5]}"
                )
            elif file_info[10] == 'audio':
                await update.message.reply_audio(
                    audio=file_id,
                    caption=f"📁 {file_info[2]}\n📥 Downloads: {file_info[5]}"
                )
            else:
                await update.message.reply_document(
                    document=file_id,
                    caption=f"📁 {file_info[2]}\n📥 Downloads: {file_info[5]}"
                )
                
        except Exception as e:
            logger.error(f"Error sending file: {e}")
            await update.message.reply_text("❌ Error sending file!")
    
    async def my_files(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's uploaded files"""
        user_id = update.effective_user.id
        
        # Get files from database (customize this query)
        files = db.get_all_files(limit=10)
        
        if not files:
            await update.message.reply_text("📁 Aapne abhi tak koi file upload nahi ki!")
            return
        
        text = "📁 **Aapki Files:**\n\n"
        for file in files:
            text += f"📄 {file[1]}\n"  # file_name
            text += f"📊 Size: {self.format_size(file[2])}\n"
            text += f"📥 Downloads: {file[3]}\n"
            text += f"🔗 Link: /start_{file[5]}\n\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def search_files(self, update: Update, context: ContextTypes.DEFAULT_TYPE, query):
        """Search files"""
        results = db.search_files(query)
        
        if not results:
            await update.message.reply_text(f"❌ '{query}' se koi file nahi mili!")
            return
        
        text = f"🔍 **Search Results for '{query}':**\n\n"
        for file in results:
            text += f"📄 {file[1]}\n"
            text += f"📊 {self.format_size(file[2])}\n"
            text += f"🔗 /get_{file[0]}\n\n"
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot statistics"""
        stats = db.get_stats()
        
        text = f"""
📊 **Bot Statistics**

📁 **Total Files:** {stats['total_files']}
💾 **Total Storage:** {self.format_size(stats['total_size'])}
📥 **Total Downloads:** {stats['total_downloads']}
👥 **Active Users:** {stats['total_users']}

🕐 Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Help command"""
        help_text = """
🆘 **Help Menu**

**📤 Upload Files:**
1. Group mein join karein
2. File bhejen
3. Bot link generate karega

**📥 Download Files:**
• Link par click karen
• Ya bot mein /start_LINK bhejen

**🔍 Search Files:**
/search filename

**📊 Commands:**
/start - Start bot
/myfiles - Your files
/stats - Bot stats
/search - Search
/help - This menu

**📌 Note:** Sirf supported groups mein upload ho sakta hai!

Need help? Contact @Admin
        """
        
        keyboard = [
            [InlineKeyboardButton("📢 Join Group", url=GROUP_LINK)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button clicks"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == "myfiles":
            await self.my_files(update, context)
        elif data == "search":
            await query.edit_message_text("🔍 Search query bhejen: /search filename")
        elif data.startswith("copy_"):
            custom_link = data.replace("copy_", "")
            bot_username = context.bot.username
            file_url = f"https://t.me/{bot_username}?start={custom_link}"
            await query.edit_message_text(f"🔗 **Copy this link:**\n\n`{file_url}`", parse_mode=ParseMode.MARKDOWN)
        elif data.startswith("get_"):
            custom_link = data.replace("get_", "")
            await self.send_file_by_link(update, context, custom_link)
    
    def format_size(self, size_bytes):
        """Format file size"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def run(self):
        """Run the bot"""
        # Create application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("myfiles", self.my_files))
        application.add_handler(CommandHandler("stats", self.stats))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("search", self.search_files))
        
        # Message handlers
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, 
            self.handle_private_message
        ))
        application.add_handler(MessageHandler(
            filters.ALL & filters.ChatType.GROUP, 
            self.handle_group_message
        ))
        
        # Callback handler
        application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Start bot
        print("🤖 Bot started! Press Ctrl+C to stop.")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    bot = StorageBot()
    bot.run()
