"""
Classe Cart – Gestione del carrello tramite sessione Flask

Questa classe implementa un carrello semplice e persistente usando la sessione
di Flask. Ogni utente ha il proprio carrello salvato in session['cart'], senza
bisogno di database.
"""

from flask import session
from decimal import Decimal
from app.models import Prodotto

class Cart:
    def __init__(self):
        if 'cart' not in session:
            session['cart'] = {}
        self.cart = session['cart']

    def add(self, prodotto, quantita=1):
        pid = str(prodotto.id)
        if pid not in self.cart:
            self.cart[pid] = {
                'qty': 0,
                'price': str(prodotto.prezzo),
                'nome': prodotto.nome
            }
        self.cart[pid]['qty'] += quantita
        self.save()

    def remove(self, prodotto_id):
        pid = str(prodotto_id)
        if pid in self.cart:
            del self.cart[pid]
            self.save()

    def update(self, prodotto_id, quantita):
        pid = str(prodotto_id)
        if pid in self.cart:
            if quantita > 0:
                self.cart[pid]['qty'] = quantita
            else:
                del self.cart[pid]
            self.save()

    def clear(self):
        session['cart'] = {}
        self.cart = session['cart']
        self.save()

    def get_items(self):
        items = []
        for pid, item in self.cart.items():
            prodotto = Prodotto.query.get(int(pid))
            if prodotto:
                items.append({
                    'id': pid,
                    'nome': item['nome'],
                    'price': Decimal(item['price']),
                    'qty': item['qty'],
                    'max_qty': prodotto.quantita
                })
        return items

    def get_total(self):
        return sum(Decimal(item['price']) * item['qty'] for item in self.cart.values())

    def save(self):
        session.modified = True

    def __len__(self):
        return sum(item['qty'] for item in self.cart.values())

    #  rende il carrello iterabile
    def __iter__(self):
        for pid, item in self.cart.items():
            yield {
                'prodotto_id': int(pid),
                'nome': item['nome'],
                'qty': item['qty'],
                'price': Decimal(item['price']),
                'subtotal': Decimal(item['price']) * item['qty']
            }