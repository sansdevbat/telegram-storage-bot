import os

# Bot Configuration
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
GROUP_ID = os.environ.get('GROUP_ID', '-1001234567890')  # Your group ID

# Database
DATABASE_NAME = 'storage.db'

# Admin IDs (jo bot ko control kar sakte hain)
ADMIN_IDS = [123456789, 987654321]  # Apne Telegram IDs daalein

# Channel/Group Links
GROUP_LINK = "https://t.me/your_group"  # Apna group link
CHANNEL_LINK = "https://t.me/your_channel"  # Agar channel bhi hai to

# File size limit (in MB)
MAX_FILE_SIZE = 2000  # 2GB limit
