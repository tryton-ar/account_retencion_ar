# This file is part of the account_retencion_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal

from trytond import backend
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool
from trytond.pyson import Eval, Bool, Not, Id
from trytond.transaction import Transaction
from trytond.exceptions import UserError
from trytond.i18n import gettext
from trytond.tools.multivalue import migrate_property
from trytond.modules.company.model import (
    CompanyMultiValueMixin, CompanyValueMixin)


class TaxWithholdingType(ModelSQL, ModelView, CompanyMultiValueMixin):
    'Tax Withholding Type'
    __name__ = 'account.retencion'

    name = fields.Char('Name', required=True)
    type = fields.Selection([
        ('efectuada', 'Submitted'),
        ('soportada', 'Received'),
        ], 'Type', required=True)
    account = fields.Many2One('account.account', 'Account', required=True,
        domain=[
            ('type', '!=', None),
            ('closed', '!=', True),
            ])
    sequence = fields.MultiValue(fields.Many2One(
        'ir.sequence', 'Sequence',
        domain=[
            ('sequence_type', '=',
                Id('account_retencion_ar', 'seq_type_account_retencion')),
            ('company', 'in',
                [Eval('context', {}).get('company', -1), None]),
            ],
        states={'invisible': Eval('type') != 'efectuada'}))
    sequences = fields.One2Many('account.retencion.sequence',
        'retencion', 'Sequences')

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'sequence':
            return pool.get('account.retencion.sequence')
        return super().multivalue_model(field)


class TaxWithholdingTypeSequence(ModelSQL, CompanyValueMixin):
    'Tax Withholding Type Sequence'
    __name__ = 'account.retencion.sequence'

    retencion = fields.Many2One('account.retencion', 'Tax Withholding Type',
        ondelete='CASCADE', context={'company': Eval('company', -1)},
        depends={'company'})
    sequence = fields.Many2One('ir.sequence',
        'Sequence', domain=[
            ('sequence_type', '=',
                Id('account_retencion_ar', 'seq_type_account_retencion')),
            ('company', 'in', [Eval('company', -1), None]),
            ])

    @classmethod
    def __register__(cls, module_name):
        exist = backend.TableHandler.table_exist(cls._table)
        super().__register__(module_name)
        if not exist:
            cls._migrate_property([], [], [])

    @classmethod
    def _migrate_property(cls, field_names, value_names, fields):
        field_names.append('sequence')
        value_names.append('sequence')
        fields.append('company')
        migrate_property(
            'account.retencion', field_names, cls, value_names,
            parent='retencion', fields=fields)


class TaxWithholdingSubmitted(ModelSQL, ModelView):
    'Tax Withholding Submitted'
    __name__ = 'account.retencion.efectuada'

    _states = {'readonly': Eval('state') != 'draft'}

    name = fields.Char('Number',
        states={
            'required': Bool(Eval('name_required')),
            'readonly': Not(Bool(Eval('name_required'))),
            })
    name_required = fields.Function(fields.Boolean('Name Required'),
        'on_change_with_name_required')
    tax = fields.Many2One('account.retencion', 'Type',
        domain=[('type', '=', 'efectuada')], states=_states)
    aliquot = fields.Float('Aliquot')
    date = fields.Date('Date', required=True, states=_states)
    voucher = fields.Many2One('account.voucher', 'Voucher', readonly=True)
    party = fields.Many2One('party.party', 'Party', states=_states)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('cancelled', 'Cancelled'),
        ], 'State', readonly=True)
    amount = fields.Numeric('Amount', digits=(16, 2), required=True,
        states=_states)

    del _states

    @classmethod
    def __register__(cls, module_name):
        cursor = Transaction().connection.cursor()
        sql_table = cls.__table__()
        super().__register__(module_name)
        cursor.execute(*sql_table.update(
                [sql_table.state], ['cancelled'],
                where=sql_table.state == 'canceled'))

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_date():
        Date = Pool().get('ir.date')
        return Date.today()

    @staticmethod
    def default_amount():
        return Decimal('0.00')

    @fields.depends('tax')
    def on_change_with_name_required(self, name=None):
        if self.tax and self.tax.sequence:
            return False
        return True

    @classmethod
    def delete(cls, retenciones):
        cls.check_delete(retenciones)
        super().delete(retenciones)

    @classmethod
    def check_delete(cls, retenciones):
        for retencion in retenciones:
            if retencion.voucher:
                raise UserError(gettext(
                    'account_retencion_ar.msg_not_delete',
                    retention=retencion.name))

    @classmethod
    def copy(cls, retenciones, default=None):
        if default is None:
            default = {}
        current_default = default.copy()
        current_default['state'] = 'draft'
        current_default['name'] = None
        current_default['voucher'] = None
        return super().copy(retenciones, default=current_default)


class TaxWithholdingReceived(ModelSQL, ModelView):
    'Tax Withholding Received'
    __name__ = 'account.retencion.soportada'

    _states = {'readonly': Eval('state') != 'draft'}

    name = fields.Char('Number', required=True, states=_states)
    tax = fields.Many2One('account.retencion', 'Type',
        domain=[('type', '=', 'soportada')], states=_states)
    date = fields.Date('Date', required=True, states=_states)
    voucher = fields.Many2One('account.voucher', 'Voucher', readonly=True)
    party = fields.Many2One('party.party', 'Party', states=_states)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('held', 'Held'),
        ('cancelled', 'Cancelled'),
        ], 'State', readonly=True)
    amount = fields.Numeric('Amount', digits=(16, 2), required=True,
        states=_states)

    del _states

    @classmethod
    def __register__(cls, module_name):
        cursor = Transaction().connection.cursor()
        sql_table = cls.__table__()
        super().__register__(module_name)
        cursor.execute(*sql_table.update(
                [sql_table.state], ['cancelled'],
                where=sql_table.state == 'canceled'))

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_date():
        Date = Pool().get('ir.date')
        return Date.today()

    @staticmethod
    def default_amount():
        return Decimal('0.00')

    @classmethod
    def delete(cls, retenciones):
        cls.check_delete(retenciones)
        super().delete(retenciones)

    @classmethod
    def check_delete(cls, retenciones):
        for retencion in retenciones:
            if retencion.voucher:
                raise UserError(gettext(
                    'account_retencion_ar.msg_not_delete',
                    retention=retencion.name))

    @classmethod
    def copy(cls, retenciones, default=None):
        if default is None:
            default = {}
        current_default = default.copy()
        current_default['state'] = 'draft'
        current_default['name'] = None
        current_default['voucher'] = None
        return super().copy(retenciones, default=current_default)
