import logging
import os
import sqlite3
import stripe
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_ID, MIN_DEPOSIT, BOT_USERNAME, SUPPORT_USERNAME, GROUP_URL, STRIPE_API_KEY

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Configurar Stripe
stripe.api_key = STRIPE_API_KEY

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('joao_store.db', check_same_thread=False)
        self.create_tables()
        self.create_sample_products()
    
    def create_tables(self):
        cursor = self.conn.cursor()
        
        # Tabela de usuários
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance REAL DEFAULT 0.0,
                referral_code TEXT,
                referred_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de produtos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                stock INTEGER DEFAULT 0,
                category TEXT DEFAULT 'logins',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de pedidos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product_id INTEGER,
                price REAL,
                credentials TEXT,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de transações
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                type TEXT,
                payment_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def create_sample_products(self):
        """Criar produtos de exemplo"""
        cursor = self.conn.cursor()
        
        # Verificar se já existem produtos
        cursor.execute('SELECT COUNT(*) FROM products')
        if cursor.fetchone()[0] == 0:
            sample_products = [
                ("NETFLIX PREMIUM (TELA)", "Acesso premium ao Netflix", 11.00, 50),
                ("MAX HBO (TELA)", "Acesso ao Max HBO", 3.00, 30),
                ("PRIME VIDEO (TELA)", "Acesso ao Prime Video", 3.00, 40),
                ("DISNEY+ (TELA)", "Acesso ao Disney+", 5.00, 35),
                ("YOUTUBE PREMIUM", "YouTube Premium familiar", 8.00, 25)
            ]
            
            for name, desc, price, stock in sample_products:
                cursor.execute(
                    'INSERT INTO products (name, description, price, stock) VALUES (?, ?, ?, ?)',
                    (name, desc, price, stock)
                )
            
            self.conn.commit()
    
    def add_user(self, user_id, username, first_name):
        cursor = self.conn.cursor()
        referral_code = f"REF{user_id}"
        cursor.execute(
            'INSERT OR IGNORE INTO users (user_id, username, first_name, referral_code) VALUES (?, ?, ?, ?)',
            (user_id, username, first_name, referral_code)
        )
        self.conn.commit()
    
    def get_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        return cursor.fetchone()
    
    def update_balance(self, user_id, amount):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        self.conn.commit()
    
    def get_products(self, category=None):
        cursor = self.conn.cursor()
        if category:
            cursor.execute('SELECT * FROM products WHERE category = ? AND is_active = TRUE', (category,))
        else:
            cursor.execute('SELECT * FROM products WHERE is_active = TRUE')
        return cursor.fetchall()
    
    def get_product(self, product_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        return cursor.fetchone()
    
    def create_order(self, user_id, product_id, credentials):
        cursor = self.conn.cursor()
        product = self.get_product(product_id)
        cursor.execute(
            'INSERT INTO orders (user_id, product_id, price, credentials) VALUES (?, ?, ?, ?)',
            (user_id, product_id, product[3], credentials)
        )
        # Atualizar estoque
        cursor.execute('UPDATE products SET stock = stock - 1 WHERE id = ?', (product_id,))
        self.conn.commit()
        return cursor.lastrowid
    
    def add_transaction(self, user_id, amount, payment_id, type='deposit'):
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT INTO transactions (user_id, amount, type, payment_id) VALUES (?, ?, ?, ?)',
            (user_id, amount, type, payment_id)
        )
        self.conn.commit()
        return cursor.lastrowid
    
    def complete_transaction(self, payment_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM transactions WHERE payment_id = ?', (payment_id,))
        transaction = cursor.fetchone()
        
        if transaction and transaction[5] == 'pending':
            cursor.execute('UPDATE transactions SET status = "completed" WHERE payment_id = ?', (payment_id,))
            cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (transaction[2], transaction[1]))
            self.conn.commit()
            return True
        return False

# Inicializar banco de dados
db = Database()

# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Adicionar usuário ao banco de dados
    db.add_user(user_id, user.username, user.first_name)
    user_data = db.get_user(user_id)
    balance = user_data[3] if user_data else 0.0
    
    # Mensagem de boas-vindas
    welcome_text = f"""
🥇 *Descubra como nosso bot pode transformar sua experiência de compras!*

Ele facilita a busca por diversos produtos e serviços, garantindo que você encontre o que precisa com o melhor preço e excelente custo-benefício.

*Importante:* Não realizamos reembolsos em dinheiro. O suporte estará disponível por até 48 horas após a entrega das informações, com reembolso em créditos no bot, se necessário.

👥 *Grupo De Clientes:* {GROUP_URL}

👨‍💻 *Link De Suporte:* {SUPPORT_USERNAME}

*ℹ️Seus Dados:*
🆔 *ID:* `{user_id}`
💸 *Saldo Atual:* R${balance:.2f}
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
            InlineKeyboardButton("👩‍💻 Suporte", url=SUPPORT_URL)
        ],
        [
            InlineKeyboardButton("ℹ️ Informações", callback_data="info"),
            InlineKeyboardButton("🔎 Pesquisar Serviços", callback_data="search_services")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(
            welcome_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await update.callback_query.edit_message_text(
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

🗒️ *Descrição:* {product[2]}

*Aviso Importante:*
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
    credentials = f"email: usuario{user[0]}@joaostore.com\nsenha: {user[0]}{product_id}"
    
    order_id = db.create_order(user[0], product_id, credentials)
    db.update_balance(user[0], -product[3])
    
    text = f"""
✅ *Compra realizada com sucesso!*

📦 *Produto:* {product[1]}
💰 *Valor:* R${product[3]:.2f}
🆔 *Pedido:* #{order_id}

*Credenciais:*
    
♻️ *Garantia:* 30 dias
📞 *Suporte:* {SUPPORT_USERNAME}
    """
    
    keyboard = [
        [InlineKeyboardButton("🛒 Comprar Novamente", callback_data="premium_products")],
        [InlineKeyboardButton("↩️ Voltar ao Início", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Handler para recarga
async def recharge_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = db.get_user(query.from_user.id)
    
    text = f"""
💼 *ID da Carteira:* `{user[0]}`
💵 *Saldo Disponível:* R${user[3]:.2f}

💡 *Selecione uma opção para recarregar:*
    """
    
    keyboard = [
        [InlineKeyboardButton("💳 PIX AUTOMÁTICO", callback_data="pix_payment")],
        [InlineKeyboardButton("↩️ Voltar", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Handler para pagamento PIX
async def pix_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = f"""
ℹ️ *Informe o valor que deseja recarregar:*

🔻 *Recarga mínima:* R${MIN_DEPOSIT:.2f}

⚠️ *Por favor, envie o valor que deseja recarregar agora.*
    """
    
    await query.edit_message_text(text, parse_mode='Markdown')
    context.user_data['awaiting_amount'] = True

# Handler para mensagens de texto (valor da recarga)
async def handle_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_amount'):
        return
    
    try:
        amount = float(update.message.text.replace(',', '.'))
        
        if amount < MIN_DEPOSIT:
            await update.message.reply_text(f"❌ Valor mínimo é R${MIN_DEPOSIT:.2f}")
            return
        
        user_id = update.effective_user.id
        
        # Criar sessão de checkout do Stripe
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'brl',
                        'product_data': {
                            'name': f'Recarga JOÃO STORE - R${amount:.2f}',
                        },
                        'unit_amount': int(amount * 100),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f'https://t.me/{BOT_USERNAME.replace("@", "")}?start=payment_success',
                cancel_url=f'https://t.me/{BOT_USERNAME.replace("@", "")}?start=payment_cancel',
                metadata={
                    'user_id': user_id,
                    'amount': amount
                }
            )
            
            # Salvar transação
            db.add_transaction(user_id, amount, session.id)
            
            text = f"""
*Gerando pagamento...*

💰 *Comprar Saldo com PIX Automático:*

⏱️ *Expira em:* 30 minutos
💵 *Valor:* R${amount:.2f}
✨ *ID da Recarga:* `{session.id}`

🗞️ *Atenção:* Este código é válido para apenas um único pagamento.
Se você utilizá-lo mais de uma vez, o saldo adicional será perdido sem direito a reembolso.

💎 *Link de Pagamento:*
{session.url}

💡 *Dica:* Clique no link acima para pagar.

🇧🇷 *Após o pagamento, seu saldo será liberado instantaneamente.*
            """
            
            keyboard = [
                [InlineKeyboardButton("⏰ Verificar Pagamento", callback_data=f"check_payment_{session.id}")],
                [InlineKeyboardButton("↩️ Voltar", callback_data="recharge")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        
        except Exception as e:
            await update.message.reply_text("❌ Erro ao processar pagamento. Tente novamente.")
            print(f"Stripe error: {e}")
        
        context.user_data['awaiting_amount'] = False
        
    except ValueError:
        await update.message.reply_text("❌ Por favor, envie apenas números!")

# Handler para verificar pagamento
async def check_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    session_id = query.data.split('_')[-1]
    
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        
        if session.payment_status == 'paid':
            if db.complete_transaction(session_id):
                user = db.get_user(query.from_user.id)
                text = f"✅ *Pagamento confirmado!*\n\nSeu saldo foi atualizado para: R${user[3]:.2f}"
            else:
                text = "❌ *Pagamento já processado anteriormente.*"
        else:
            text = "⏳ *Pagamento ainda não confirmado.*\n\nTente novamente em alguns instantes."
    except Exception as e:
        text = "❌ *Erro ao verificar pagamento.*"
        print(f"Payment check error: {e}")
    
    keyboard = [[InlineKeyboardButton("↩️ Voltar", callback_data="recharge")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Handler para perfil do usuário
async def user_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user = db.get_user(query.from_user.id)
    
    text = f"""
🙋‍♂️ *Meu Perfil*

🔎 *Veja aqui os detalhes da sua conta:*

*-👤 Informações:*
🆔 *ID da Carteira:* `{user[0]}`
💰 *Saldo Atual:* R${user[3]:.2f}

*📊 Suas movimentações:*
—🛒 *Compras Realizadas:* 0
—💠 *Pix Inseridos:* R$0,00
—🎁 *Gifts Resgatados:* R$0,00
    """
    
    keyboard = [
        [InlineKeyboardButton("🛍️ Histórico De Compras", callback_data="purchase_history")],
        [InlineKeyboardButton("↩️ Voltar", callback_data="back_to_main")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Handler para voltar ao menu principal
async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await start(update, context)

# Handler para informações
async def bot_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = f"""
ℹ️ *SOFTWARE INFO:*
🤖 *BOT:* {BOT_USERNAME}
🤖 *VERSION:* 2.0

🛠️ *DEVELOPER INFO:*
O Desenvolvedor não possui responsabilidade alguma sobre este Bot e nem sobre o adm do mesmo, caso entre em contato para reclamar sobre material ou pedir para chamar o adm deste Bot ou algo do tipo, será bloqueado de imediato... Apenas o chame, caso queira conhecer os Bots disponíveis.
    """
    
    keyboard = [[InlineKeyboardButton("↩️ Voltar", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Handler para ranking
async def show_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = """
🏆 *Ranking dos serviços mais vendidos*

1️⃣ *Em desenvolvimento...*
    """
    
    keyboard = [[InlineKeyboardButton("↩️ Voltar", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Handler principal
def main():
    # Criar aplicação
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Handlers de comandos
    application.add_handler(CommandHandler("start", start))
    
    # Handlers de callback
    application.add_handler(CallbackQueryHandler(start, pattern="^back_to_main$"))
    application.add_handler(CallbackQueryHandler(premium_products, pattern="^premium_products$"))
    application.add_handler(CallbackQueryHandler(view_product, pattern="^product_"))
    application.add_handler(CallbackQueryHandler(buy_product, pattern="^buy_"))
    application.add_handler(CallbackQueryHandler(recharge_menu, pattern="^recharge$"))
    application.add_handler(CallbackQueryHandler(pix_payment, pattern="^pix_payment$"))
    application.add_handler(CallbackQueryHandler(check_payment, pattern="^check_payment_"))
    application.add_handler(CallbackQueryHandler(user_profile, pattern="^profile$"))
    application.add_handler(CallbackQueryHandler(bot_info, pattern="^info$"))
    application.add_handler(CallbackQueryHandler(show_ranking, pattern="^ranking$"))
    
    # Handler para mensagens de texto
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_amount))
    
    # Iniciar bot
    print("🤖 Bot JOÃO STORE iniciado!")
    application.run_polling()

if __name__ == '__main__':
    main()
