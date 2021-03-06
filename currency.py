# -*- coding: utf-8 -*-
"""
    currency

"""
from trytond.model import ModelSQL, fields
from trytond.transaction import Transaction
from trytond.pool import Pool, PoolMeta


__all__ = [
    'CurrencyPrestashop', 'Currency'
]
__metaclass__ = PoolMeta


class CurrencyPrestashop(ModelSQL):
    """Prestashop currency cache

    This model keeps a store of tryton currency corresponding to the currency
    on prestashop as per prestashop channel.
    This model is used to prevent extra API calls to be sent to prestashop
    to get the currency.
    Everytime a currency has to be looked up, it is first looked up in this
    model. If not found, a new record is created here.
    """
    __name__ = 'currency.currency.prestashop'

    currency = fields.Many2One('currency.currency', 'Currency', required=True)
    channel = fields.Many2One('sale.channel', 'Channel', required=True)
    prestashop_id = fields.Integer('Prestashop ID', required=True)

    @staticmethod
    def default_channel():
        "Return default channel from context"
        return Transaction().context.get('current_channel')

    @classmethod
    def __setup__(cls):
        super(CurrencyPrestashop, cls).__setup__()
        cls._error_messages.update({
            'currency_not_found': 'Currency with code %s not found',
        })
        cls._sql_constraints += [
            (
                'prestashop_id_channel_uniq',
                'UNIQUE(prestashop_id, channel)',
                'Currency must be unique by prestashop id and channel'
            )
        ]


class Currency:
    "Currency"
    __name__ = 'currency.currency'

    @classmethod
    def get_using_ps_id(cls, prestashop_id):
        """Return the currency corresponding to the prestashop_id for the
        current channel in context
        If the currency is not found in the cache model, it is fetched from
        remote and a record is created in the cache for future references.

        :param prestashop_id: Prestashop ID for the currency
        :returns: Active record of the currency
        """
        CurrencyPrestashop = Pool().get('currency.currency.prestashop')

        records = CurrencyPrestashop.search([
            ('channel', '=', Transaction().context.get('current_channel')),
            ('prestashop_id', '=', prestashop_id)
        ])

        if records:
            return records[0].currency
        # Currency is not cached yet, cache it and return
        return cls.cache_prestashop_id(prestashop_id)

    @classmethod
    def cache_prestashop_id(cls, prestashop_id):
        """Cache the value of currency corresponding to the prestashop_id
        by creating a record in the cache model

        :param prestashop_id: Prestashop ID
        :returns: Active record of the currency cached
        """
        SaleChannel = Pool().get('sale.channel')
        CurrencyPrestashop = Pool().get('currency.currency.prestashop')

        channel = SaleChannel(Transaction().context.get('current_channel'))
        channel.validate_prestashop_channel()

        client = channel.get_prestashop_client()

        currency_data = client.currencies.get(prestashop_id)
        currency = cls.search([('code', '=', currency_data.iso_code.pyval)])

        if not currency:
            cls.raise_user_error(
                'currency_not_found', (currency_data.iso_code.pyval,)
            )
        CurrencyPrestashop.create([{
            'currency': currency[0].id,
            'channel': channel.id,
            'prestashop_id': prestashop_id,
        }])

        return currency and currency[0] or None
