# This file is part of the account_retencion_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal

from trytond.model import ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Or
from trytond.exceptions import UserError
from trytond.i18n import gettext


class AccountVoucher(metaclass=PoolMeta):
    __name__ = 'account.voucher'

    retenciones_efectuadas = fields.One2Many('account.retencion.efectuada',
        'voucher', 'Tax Withholding Submitted',
        states={
            'invisible': Eval('voucher_type') != 'payment',
            'readonly': Or(
                Eval('state') == 'posted',
                Eval('currency_code') != 'ARS'),
            })
    retenciones_soportadas = fields.One2Many('account.retencion.soportada',
        'voucher', 'Tax Withholding Received',
        states={
            'invisible': Eval('voucher_type') != 'receipt',
            'readonly': Or(
                Eval('state') == 'posted',
                Eval('currency_code') != 'ARS'),
            })

    @fields.depends('retenciones_efectuadas', 'retenciones_soportadas')
    def on_change_with_amount(self, name=None):
        amount = super().on_change_with_amount(name)
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
        move_lines = super().prepare_move_lines()
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
        TaxWithholdingReceived = pool.get('account.retencion.soportada')
        TaxWithholdingSubmitted = pool.get('account.retencion.efectuada')

        super().post(vouchers)

        for voucher in vouchers:
            if voucher.retenciones_soportadas:
                TaxWithholdingReceived.write(list(
                        voucher.retenciones_soportadas), {
                    'party': voucher.party.id,
                    'state': 'held',
                    })
            if voucher.retenciones_efectuadas:
                for retencion in voucher.retenciones_efectuadas:
                    if not retencion.tax.sequence:
                        raise UserError(gettext(
                            'account_retencion_ar.msg_missing_retencion_seq'))

                    TaxWithholdingSubmitted.write([retencion], {
                        'party': voucher.party.id,
                        'name': retencion.tax.sequence.get(),
                        'state': 'issued',
                        })

    @classmethod
    @ModelView.button
    def cancel(cls, vouchers):
        pool = Pool()
        TaxWithholdingReceived = pool.get('account.retencion.soportada')
        TaxWithholdingSubmitted = pool.get('account.retencion.efectuada')

        super().cancel(vouchers)

        for voucher in vouchers:
            if voucher.retenciones_soportadas:
                TaxWithholdingReceived.write(list(
                        voucher.retenciones_soportadas), {
                    'party': None,
                    'state': 'cancelled',
                    })
            if voucher.retenciones_efectuadas:
                TaxWithholdingSubmitted.write(list(
                        voucher.retenciones_efectuadas), {
                    'party': None,
                    'state': 'cancelled',
                    })
