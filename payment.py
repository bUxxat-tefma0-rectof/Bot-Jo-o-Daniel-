import stripe
from config import STRIPE_API_KEY

stripe.api_key = STRIPE_API_KEY

class PaymentSystem:
    @staticmethod
    def create_payment_link(amount, description, user_id):
        try:
            # Converter para centavos
            amount_cents = int(amount * 100)
            
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'brl',
                        'product_data': {
                            'name': f'Recarga - R${amount:.2f}',
                            'description': description,
                        },
                        'unit_amount': amount_cents,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f'https://t.me/JOAOSTORE_BOT?start=payment_success_{user_id}',
                cancel_url=f'https://t.me/JOAOSTORE_BOT?start=payment_cancel',
                metadata={
                    'user_id': user_id,
                    'amount': amount
                }
            )
            
            return session.url, session.id
        except Exception as e:
            print(f"Erro ao criar link de pagamento: {e}")
            return None, None
    
    @staticmethod
    def verify_payment(session_id):
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            return session.payment_status == 'paid'
        except Exception as e:
            print(f"Erro ao verificar pagamento: {e}")
            return False
