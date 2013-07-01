#This file is part of the account_retencion_ar module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from decimal import Decimal
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool

__all__ = ['AccountRetencion', 'AccountRetencionEfectuada',
    'AccountRetencionSoportada']


class AccountRetencion(ModelSQL, ModelView):
    "Account Retencion"
    __name__ = 'account.retencion'

    name = fields.Char('Name', required=True)
    account = fields.Many2One('account.account', 'Account', required=True)
    type = fields.Selection([
        ('efectuada', 'Efectuada'),
        ('soportada', 'Soportada'),
        ], 'Type', required=True)


class AccountRetencionEfectuada(ModelSQL, ModelView):
    'Account Retencion Efectuada'
    __name__ = 'account.retencion.efectuada'

    name = fields.Char('Number', required=True)
    amount = fields.Numeric('Amount', digits=(16, 2), required=True)
    aliquot = fields.Float('Aliquot')
    date = fields.Date('Date', required=True)
    tax = fields.Many2One('account.retencion', 'Tax',
        domain=[('type', '=', 'efectuada')])
    voucher = fields.Many2One('account.voucher', 'Voucher')
    party = fields.Many2One('party.party', 'Party')

    @staticmethod
    def default_amount():
        return Decimal('0.00')

    @staticmethod
    def default_date():
        Date = Pool().get('ir.date')
        return Date.today()


class AccountRetencionSoportada(ModelSQL, ModelView):
    'Account Retencion Soportada'
    __name__ = 'account.retencion.soportada'

    name = fields.Char('Number', required=True)
    amount = fields.Numeric('Amount', digits=(16, 2), required=True)
    date = fields.Date('Date', required=True)
    tax = fields.Many2One('account.retencion', 'Tax',
        domain=[('type', '=', 'soportada')])
    voucher = fields.Many2One('account.voucher', 'Voucher')
    party = fields.Many2One('party.party', 'Party')

    @staticmethod
    def default_amount():
        return Decimal('0.00')

    @staticmethod
    def default_date():
        Date = Pool().get('ir.date')
        return Date.today()
