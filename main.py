import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_ID, MIN_DEPOSIT, BOT_USERNAME, SUPPORT_USERNAME, GROUP_URL
from database import Database
from payment import PaymentSystem
import json
from datetime import datetime

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

db = Database()
payment_system = PaymentSystem()

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Adicionar usuário ao banco de dados
    db.add_user(user_id, user.username, user.first_name)
    
    # Mensagem de boas-vindas
    welcome_text = f"""
🥇 *Descubra como nosso bot pode transformar sua experiência de compras!*

Ele facilita a busca por diversos produtos e serviços, garantindo que você encontre o que precisa com o melhor preço e excelente custo-benefício.

*Importante:* Não realizamos reembolsos em dinheiro. O suporte estará disponível por até 48 horas após a entrega das informações, com reembolso em créditos no bot, se necessário.

👥 *Grupo De Clientes:* {GROUP_URL}

👨‍💻 *Link De Suporte:* {SUPPORT_USERNAME}

*ℹ️Seus Dados:*
🆔 *ID:* `{user_id}`
💸 *Saldo Atual:* R$0,00
🪪 *Usuário:* @{user.username if user.username else 'N/A'}
    """
    
    keyboard = [
        [
            InlineKeyboardButton("💎 Logins | Contas Premium", callback_data="premium_products")
        ],
        [
            InlineKeyboardButton("🪪 PERFIL", callback_data="profile"),
            InlineKeyboardButton("💰 RECARGA", callback_data="recharge")
        ],
        [
            InlineKeyboardButton("🎖️ Ranking", callback_data="ranking"),
            InlineKeyboardButton("👩‍💻 Suporte", url=SUPPORT_USERNAME)
        ],
        [
            InlineKeyboardButton("ℹ️ Informações", callback_data="info"),
            InlineKeyboardButton("🔎 Pesquisar Serviços", callback_data="search_services")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Handler para produtos premium
async def premium_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = db.get_user(query.from_user.id)
    balance = user[3] if user else 0
    
    products = db.get_products('logins')
    
    text = f"""
🎟️ *Logins Premium | Acesso Exclusivo*

🏦 *Carteira*
💸 *Saldo Atual:* R${balance:.2f}

*Produtos Disponíveis:*
    """
    
    keyboard = []
    for product in products:
        keyboard.append([
            InlineKeyboardButton(
                f"{product[1]} - R${product[3]:.2f}", 
                callback_data=f"product_{product[0]}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("↩️ Voltar", callback_data="back_to_main")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Handler para visualização de produto
async def view_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split('_')[1])
    product = db.get_product(product_id)
    user = db.get_user(query.from_user.id)
    balance = user[3] if user else 0
    
    if product:
        text = f"""
⚜️ *ACESSO:* {product[1]}

💵 *Preço:* R${product[3]:.2f}
💼 *Saldo Atual:* R${balance:.2f}
📥 *Estoque Disponível:* {product[4]}

🗒️ *Descrição:* Aviso Importante:
O acesso é disponibilizado na hora. Não atendemos ligações nem ouvimos mensagens de áudio; pedimos que aguarde sua vez.
Informamos que não realizamos reembolsos via Pix, apenas em créditos no bot, correspondendo aos dias restantes até o vencimento.
Agradecemos pela compreensão e desejamos boas compras!

♻️ *Garantia:* 30 dias
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🛒 Comprar", callback_data=f"buy_{product_id}"),
                InlineKeyboardButton("↩️ Voltar", callback_data="premium_products")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Handler para compra de produto
async def buy_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    product_id = int(query.data.split('_')[1])
    product = db.get_product(product_id)
    user = db.get_user(query.from_user.id)
    
    if not product:
        await query.answer("Produto não encontrado!", show_alert=True)
        return
    
    if user[3] < product[3]:
        missing = product[3] - user[3]
        text = f"""
*Saldo insuficiente! Faltam R${missing:.2f}*

Faça uma recarga e tente novamente.
*Seu saldo:* R${user[3]:.2f}
        """
        
        keyboard = [
            [InlineKeyboardButton("💰 Fazer Recarga", callback_data="recharge")],
            [InlineKeyboardButton("↩️ Voltar", callback_data=f"product_{product_id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        return
    
    # Processar compra
    # Aqui você implementaria a lógica para gerar credenciais
    credentials = "email: teste@exemplo.com\nsenha: 123456"  # Exemplo
    
    order_id = db.create_order(user[0], product_id, credentials)
    db.update_balance(user[0], -product[3])
    
    text = f"""
✅ *Compra realizada com sucesso!*

📦 *Produto:* {product[1]}
💰 *Valor:* R${product[3]:.2f}
🆔 *Pedido:* #{order_id}

*Credenciais:*
