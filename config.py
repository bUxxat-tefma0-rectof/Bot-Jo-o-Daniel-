import os
from dotenv import load_dotenv

load_dotenv()

# Configurações do Bot
BOT_TOKEN = os.getenv('BOT_TOKEN', "8464485123:AAGfibOpvx6ASRrcepmQJlZ1GuoAAYml6Ws")
ADMIN_ID = int(os.getenv('ADMIN_ID', "6995978182"))

# Configurações do Stripe
STRIPE_API_KEY = os.getenv('STRIPE_API_KEY', "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")

# Configurações do Bot
BOT_USERNAME = os.getenv('BOT_USERNAME', "@JOAOSTORE_BOT")
SUPPORT_USERNAME = os.getenv('SUPPORT_USERNAME', "@suporte_joaozinstore")
MIN_DEPOSIT = float(os.getenv('MIN_DEPOSIT', "4.00"))
BONUS_PERCENTAGE = float(os.getenv('BONUS_PERCENTAGE', "0"))

# URLs
GROUP_URL = os.getenv('GROUP_URL', "https://t.me/joaostore_clientes")
SUPPORT_URL = os.getenv('SUPPORT_URL', "https://t.me/suporte_joaozinstore")
