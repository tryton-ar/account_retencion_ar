# This file is part of the account_retencion_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal

from trytond.model import ModelView, fields
from trytond.pyson import Eval, In, Not, Or
from trytond.pool import Pool, PoolMeta

__all__ = ['AccountVoucher']


class AccountVoucher(metaclass=PoolMeta):
    __name__ = 'account.voucher'

    retenciones_efectuadas = fields.One2Many('account.retencion.efectuada',
        'voucher', 'Retenciones Efectuadas',
        states={
            'invisible': Not(In(Eval('voucher_type'), ['payment'])),
            'readonly': Or(
                In(Eval('state'), ['posted']),
                Not(In(Eval('currency_code'), ['ARS']))),
            })
    retenciones_soportadas = fields.One2Many('account.retencion.soportada',
        'voucher', 'Retenciones Soportadas',
        states={
            'invisible': Not(In(Eval('voucher_type'), ['receipt'])),
            'readonly': Or(
                In(Eval('state'), ['posted']),
                Not(In(Eval('currency_code'), ['ARS']))),
            })

    @classmethod
    def __setup__(cls):
        super(AccountVoucher, cls).__setup__()
        cls._error_messages.update({
            'missing_retencion_seq': 'You must set a sequence to '
                'Retencion efecutada.',
        })

    @fields.depends('party', 'pay_lines', 'lines_credits', 'lines_debits',
        'issued_check', 'third_check', 'third_pay_checks',
        'retenciones_efectuadas', 'retenciones_soportadas')
    def on_change_with_amount(self, name=None):
        amount = super(AccountVoucher, self).on_change_with_amount(name)
        if self.retenciones_efectuadas:
            for retencion in self.retenciones_efectuadas:
                if retencion.amount:
                    amount += retencion.amount
        if self.retenciones_soportadas:
            for retencion in self.retenciones_soportadas:
                if retencion.amount:
                    amount += retencion.amount
        return amount

    def prepare_move_lines(self):
        move_lines = super(AccountVoucher, self).prepare_move_lines()
        Period = Pool().get('account.period')
        if self.voucher_type == 'receipt':
            if self.retenciones_soportadas:
                for retencion in self.retenciones_soportadas:
                    move_lines.append({
                        'debit': retencion.amount,
                        'credit': Decimal('0.0'),
                        'account': (retencion.tax.account.id if retencion.tax
                            else None),
                        'move': self.move.id,
                        'journal': self.journal.id,
                        'period': Period.find(self.company.id, date=self.date),
                        })

        if self.voucher_type == 'payment':
            if self.retenciones_efectuadas:
                for retencion in self.retenciones_efectuadas:
                    move_lines.append({
                        'debit': Decimal('0.0'),
                        'credit': retencion.amount,
                        'account': (retencion.tax.account.id if retencion.tax
                            else None),
                        'move': self.move.id,
                        'journal': self.journal.id,
                        'period': Period.find(self.company.id, date=self.date),
                        })

        return move_lines

    @classmethod
    @ModelView.button
    def post(cls, vouchers):
        pool = Pool()
        RetencionSoportada = pool.get('account.retencion.soportada')
        RetencionEfectuada = pool.get('account.retencion.efectuada')
        Sequence = pool.get('ir.sequence')

        super(AccountVoucher, cls).post(vouchers)

        for voucher in vouchers:
            if voucher.retenciones_soportadas:
                RetencionSoportada.write(list(
                        voucher.retenciones_soportadas), {
                    'party': voucher.party.id,
                    'state': 'held',
                    })
            if voucher.retenciones_efectuadas:
                for retencion in voucher.retenciones_efectuadas:
                    if not retencion.tax.sequence:
                        cls.raise_user_error('missing_retencion_seq')

                    RetencionEfectuada.write([retencion], {
                        'party': voucher.party.id,
                        'name': Sequence.get_id(retencion.tax.sequence.id),
                        'state': 'issued',
                        })

    @classmethod
    @ModelView.button
    def cancel(cls, vouchers):
        pool = Pool()
        RetencionSoportada = pool.get('account.retencion.soportada')
        RetencionEfectuada = pool.get('account.retencion.efectuada')

        super(AccountVoucher, cls).cancel(vouchers)

        for voucher in vouchers:
            if voucher.retenciones_soportadas:
                RetencionSoportada.write(list(
                        voucher.retenciones_soportadas), {
                    'party': None,
                    'state': 'canceled',
                    })
            if voucher.retenciones_efectuadas:
                RetencionEfectuada.write(list(
                        voucher.retenciones_efectuadas), {
                    'party': None,
                    'state': 'canceled',
                    })
