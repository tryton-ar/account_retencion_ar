#This file is part of the account_retencion_ar module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
from decimal import Decimal
from trytond.model import ModelView, fields
from trytond.pyson import Eval, In, Not
from trytond.pool import Pool, PoolMeta

__all__ = ['AccountVoucher']
__metaclass__ = PoolMeta


class AccountVoucher:
    __name__ = 'account.voucher'

    retenciones_efectuadas = fields.One2Many('account.retencion.efectuada',
        'voucher', 'Retenciones Efectuadas',
        states={
            'invisible': Not(In(Eval('voucher_type'), ['payment'])),
            'readonly': In(Eval('state'), ['posted']),
        })
    retenciones_soportadas = fields.One2Many('account.retencion.soportada',
        'voucher', 'Retenciones Soportadas',
        states={
            'invisible': Not(In(Eval('voucher_type'), ['receipt'])),
            'readonly': In(Eval('state'), ['posted']),
        })

    @classmethod
    def __setup__(cls):
        super(AccountVoucher, cls).__setup__()
        #cls._error_messages.update({
            #'no_journal_check_account': 'You need to define a check account '
                #'in the journal "%s",',
            #})

    @fields.depends('party', 'pay_lines', 'lines_credits', 'lines_debits',
        'issued_check', 'third_check', 'third_pay_checks', 
        'retenciones_efectuadas', 'retenciones_soportadas')
    def on_change_with_amount(self, name=None):
        amount = super(AccountVoucher, self).on_change_with_amount(name)
        if self.retenciones_efectuadas:
            for retencion in self.retenciones_efectuadas:
                amount += retencion.amount
        if self.retenciones_soportadas:
            for retencion in self.retenciones_soportadas:
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
                        'account': retencion.tax.account.id,
                        'move': self.move.id,
                        'journal': self.journal.id,
                        'period': Period.find(self.company.id, date=self.date),
                        'party': self.party.id,
                    })

        if self.voucher_type == 'payment':
            if self.retenciones_efectuadas:
                for retencion in self.retenciones_efectuadas:
                    move_lines.append({
                        'debit': Decimal('0.0'),
                        'credit': retencion.amount,
                        'account': retencion.tax.account.id,
                        'move': self.move.id,
                        'journal': self.journal.id,
                        'period': Period.find(self.company.id, date=self.date),
                        'party': self.party.id,
                    })

        return move_lines

    @classmethod
    @ModelView.button
    def post(cls, vouchers):
        super(AccountVoucher, cls).post(vouchers)
        RetencionSoportada = Pool().get('account.retencion.soportada')
        RetencionEfectuada = Pool().get('account.retencion.efectuada')

        for voucher in vouchers:
            if voucher.retenciones_soportadas:
                RetencionSoportada.write(list(voucher.retenciones_soportadas), {
                    'party': voucher.party.id,
                })
            if voucher.retenciones_efectuadas:
                RetencionEfectuada.write(list(voucher.retenciones_efectuadas), {
                    'party': voucher.party.id,
                })
