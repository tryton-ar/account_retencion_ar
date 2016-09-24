#This file is part of the account_retencion_ar module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from decimal import Decimal
from trytond.model import ModelView, ModelSQL, fields
from trytond.pyson import Eval, Bool, Not
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
    sequence = fields.Property(fields.Many2One('ir.sequence',
        'Retencion Sequence',
        states={
            'invisible': Eval('type') != 'efectuada',
            }, depends=['type'],
        domain=[
            ('code', '=', 'account.retencion'),
            ('company', 'in', [Eval('context', {}).get('company'), None]),
            ]))


class AccountRetencionEfectuada(ModelSQL, ModelView):
    'Account Retencion Efectuada'
    __name__ = 'account.retencion.efectuada'

    name = fields.Char('Number',
        states={
            'required': Bool(Eval('name_required')),
            'readonly': Not(Bool(Eval('name_required'))),
            },
        depends=['name_required'])
    name_required = fields.Function(fields.Boolean('Name Required'),
        'on_change_with_name_required')
    amount = fields.Numeric('Amount', digits=(16, 2), required=True)
    aliquot = fields.Float('Aliquot')
    date = fields.Date('Date', required=True)
    tax = fields.Many2One('account.retencion', 'Tax',
        domain=[('type', '=', 'efectuada')])
    voucher = fields.Many2One('account.voucher', 'Voucher')
    party = fields.Many2One('party.party', 'Party')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('canceled', 'Canceled'),
        ], 'State', readonly=True)

    @classmethod
    def __setup__(cls):
        super(AccountRetencionEfectuada, cls).__setup__()
        cls._error_messages.update({
            'not_delete': ('You cannot delete retention "%s" because '
                'it is associated to a voucher'),
            })

    @staticmethod
    def default_amount():
        return Decimal('0.00')

    @staticmethod
    def default_date():
        Date = Pool().get('ir.date')
        return Date.today()

    @fields.depends('tax')
    def on_change_with_name_required(self, name=None):
        if self.tax and self.tax.sequence:
            return False
        return True

    @staticmethod
    def default_state():
        return 'draft'

    @classmethod
    def delete(cls, retenciones):
        cls.check_delete(retenciones)
        super(AccountRetencionEfectuada, cls).delete(retenciones)

    @classmethod
    def check_delete(cls, retenciones):
        for retencion in retenciones:
            if retencion.voucher:
                cls.raise_user_error('not_delete', (retencion.name,))

    @classmethod
    def copy(cls, retenciones, default=None):
        if default is None:
            default = {}
        current_default = default.copy()
        current_default['state'] = 'draft'
        current_default['name'] = None
        current_default['voucher'] = None
        return super(AccountRetencionEfectuada, cls).copy(retenciones,
            default=current_default)


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
    state = fields.Selection([
        ('draft', 'Draft'),
        ('held', 'Held'),
        ('canceled', 'Canceled'),
        ], 'State', readonly=True)

    @classmethod
    def __setup__(cls):
        super(AccountRetencionSoportada, cls).__setup__()
        cls._error_messages.update({
            'not_delete': ('You cannot delete retention "%s" because '
                'it is associated to a voucher'),
            })

    @staticmethod
    def default_amount():
        return Decimal('0.00')

    @staticmethod
    def default_date():
        Date = Pool().get('ir.date')
        return Date.today()

    @staticmethod
    def default_state():
        return 'draft'

    @classmethod
    def delete(cls, retenciones):
        cls.check_delete(retenciones)
        super(AccountRetencionSoportada, cls).delete(retenciones)

    @classmethod
    def check_delete(cls, retenciones):
        for retencion in retenciones:
            if retencion.voucher:
                cls.raise_user_error('not_delete', (retencion.name,))

    @classmethod
    def copy(cls, retenciones, default=None):
        if default is None:
            default = {}
        current_default = default.copy()
        current_default['state'] = 'draft'
        current_default['name'] = None
        current_default['voucher'] = None
        return super(AccountRetencionSoportada, cls).copy(retenciones,
            default=current_default)
