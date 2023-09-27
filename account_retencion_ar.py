# This file is part of the account_retencion_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal
from sql import Null

from trytond import backend
from trytond.model import ModelView, ModelSQL, fields
from trytond.pool import Pool, PoolMeta
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
    tax = fields.Selection('get_tax', 'Tax', required=True, sort=False)
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
    regime_code = fields.Char('Regime code')
    regime_name = fields.Char('Regime name')
    subdivision = fields.Many2One('country.subdivision', 'Subdivision',
        domain=[('country.code', '=', 'AR')],
        states={'invisible': Eval('tax') != 'iibb'})
    minimum_non_taxable_amount = fields.Numeric('Minimum Non-Taxable Amount',
        digits=(16, 2))
    rate_registered = fields.Numeric('% Withholding to Registered',
        digits=(14, 10))
    rate_non_registered = fields.Numeric('% Withholding to Non-Registered',
        digits=(14, 10))
    minimum_withholdable_amount = fields.Numeric('Minimum Amount to Withhold',
        digits=(16, 2))
    scales = fields.One2Many('account.retencion.scale', 'retencion', 'Scales')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('type', 'ASC'))
        cls._order.insert(1, ('name', 'ASC'))
        cls._order.insert(2, ('regime_code', 'ASC'))

    @classmethod
    def get_tax(cls):
        selection = [
            ('iva', 'IVA'),
            ('gana', 'Ganancias'),
            ('suss', 'SUSS'),
            ('iibb', 'Ingresos Brutos'),
            ('otro', 'Otro'),
            ]
        return selection

    @classmethod
    def multivalue_model(cls, field):
        pool = Pool()
        if field == 'sequence':
            return pool.get('account.retencion.sequence')
        return super().multivalue_model(field)

    def get_rec_name(self, name):
        if self.regime_name:
            return '%s - %s' % (self.name, self.regime_name)
        return self.name

    @classmethod
    def view_attributes(cls):
        return super().view_attributes() + [
            ('//group[@id="calculation"]', 'states',
                {'invisible': Eval('type') != 'efectuada'}),
            ]


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


class TaxWithholdingTypeScale(ModelSQL, ModelView):
    'Tax Withholding Type Scale'
    __name__ = 'account.retencion.scale'

    retencion = fields.Many2One('account.retencion', 'Tax Withholding Type',
        ondelete='CASCADE')
    start_amount = fields.Numeric('Amount from', digits=(16, 2))
    end_amount = fields.Numeric('Amount up to', digits=(16, 2))
    fixed_withholdable_amount = fields.Numeric('Fixed Amount to Withhold',
        digits=(16, 2))
    rate = fields.Numeric('% Withholding', digits=(14, 10))
    minimum_non_taxable_amount = fields.Numeric('Non-Taxable Base',
        digits=(16, 2))

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._order.insert(0, ('start_amount', 'ASC'))


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
    regime_code = fields.Function(fields.Char('Regime code'),
        'get_tax_field')
    regime_name = fields.Function(fields.Char('Regime name'),
        'get_tax_field')
    date = fields.Date('Date', required=True, states=_states)
    voucher = fields.Many2One('account.voucher', 'Voucher', readonly=True)
    party = fields.Many2One('party.party', 'Party', states=_states)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('issued', 'Issued'),
        ('cancelled', 'Cancelled'),
        ], 'State', readonly=True)
    payment_amount = fields.Numeric('Payment Amount',
        digits=(16, 2), readonly=True)
    accumulated_amount = fields.Numeric('Accumulated Amount',
        digits=(16, 2), readonly=True)
    minimum_non_taxable_amount = fields.Numeric('Minimum Non-Taxable Amount',
        digits=(16, 2), readonly=True)
    scale_non_taxable_amount = fields.Numeric('Non-Taxable Base (Scale)',
        digits=(16, 2), readonly=True)
    taxable_amount = fields.Numeric('Taxable Amount',
        digits=(16, 2), readonly=True)
    rate = fields.Numeric('% Withholding',
        digits=(14, 10), readonly=True)
    scale_fixed_amount = fields.Numeric('Fixed Amount to Withhold (Scale)',
        digits=(16, 2), readonly=True)
    computed_amount = fields.Numeric('Computed Amount',
        digits=(16, 2), readonly=True)
    minimum_withholdable_amount = fields.Numeric('Minimum Amount to Withhold',
        digits=(16, 2), readonly=True)
    accumulated_withheld = fields.Numeric('Accumulated Withheld',
        digits=(16, 2), readonly=True)
    amount = fields.Numeric('Amount', digits=(16, 2), required=True,
        states=_states)

    del _states

    @classmethod
    def __register__(cls, module_name):
        cursor = Transaction().connection.cursor()
        sql_table = cls.__table__()
        table_h = cls.__table_handler__(module_name)

        aliquot_exist = table_h.column_exist('aliquot')

        super().__register__(module_name)
        cursor.execute(*sql_table.update(
                [sql_table.state], ['cancelled'],
                where=sql_table.state == 'canceled'))
        if aliquot_exist:
            cursor.execute(*sql_table.update(
                    [sql_table.rate], [sql_table.aliquot.cast('NUMERIC')],
                    where=sql_table.aliquot != Null))
            table_h.drop_column('aliquot')

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
        if Transaction().context.get('delete_calculated', False):
            return
        for retencion in retenciones:
            if retencion.voucher:
                raise UserError(gettext(
                    'account_retencion_ar.msg_not_delete',
                    retencion=retencion.name))

    @classmethod
    def copy(cls, retenciones, default=None):
        if default is None:
            default = {}
        current_default = default.copy()
        current_default['state'] = 'draft'
        current_default['name'] = None
        current_default['voucher'] = None
        return super().copy(retenciones, default=current_default)

    @classmethod
    def get_tax_field(cls, retenciones, names):
        result = {}
        for name in names:
            result[name] = {}
            if cls._fields[name]._type == 'many2one':
                for r in retenciones:
                    field = getattr(r.tax, name, None)
                    result[name][r.id] = field.id if field else None
            elif cls._fields[name]._type == 'boolean':
                for r in retenciones:
                    result[name][r.id] = getattr(r.tax, name, False)
            else:
                for r in retenciones:
                    result[name][r.id] = getattr(r.tax, name, None)
        return result

    @classmethod
    def search_tax_field(cls, name, clause):
        return [('tax.' + name,) + tuple(clause[1:])]


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
                    retencion=retencion.name))

    @classmethod
    def copy(cls, retenciones, default=None):
        if default is None:
            default = {}
        current_default = default.copy()
        current_default['state'] = 'draft'
        current_default['name'] = None
        current_default['voucher'] = None
        return super().copy(retenciones, default=current_default)


class Perception(metaclass=PoolMeta):
    __name__ = 'account.tax'

    subdivision = fields.Many2One('country.subdivision', 'Subdivision',
        domain=[('country.code', '=', 'AR')],
        states={'invisible': Eval('afip_kind') != 'provincial'})
    minimum_non_taxable_amount = fields.Numeric('Minimum Non-Taxable Amount',
        digits=(16, 2))
    rate_registered = fields.Numeric('% Perception to Registered',
        digits=(14, 10))
    rate_non_registered = fields.Numeric('% Perception to Non-Registered',
        digits=(14, 10))
    minimum_perceivable_amount = fields.Numeric(
        'Minimum Amount to be Perceived', digits=(16, 2))

    @classmethod
    def view_attributes(cls):
        return super().view_attributes() + [
            ('//group[@id="calculation"]', 'states',
                {'invisible': ~Eval('afip_kind').in_(
                    ['nacional', 'provincial', 'municipal'])}),
            ]
