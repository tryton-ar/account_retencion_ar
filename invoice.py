# This file is part of the account_retencion_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal

from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval
from trytond.exceptions import UserError
from trytond.i18n import gettext


class InvoiceLine(metaclass=PoolMeta):
    __name__ = 'account.invoice.line'

    ganancias_regimen = fields.Many2One('account.retencion',
        'Régimen Ganancias',
        domain=[('type', '=', 'efectuada'), ('tax', '=', 'gana')],
        states={'invisible': Eval('invoice_type') != 'in'})

    @fields.depends('product', 'invoice', '_parent_invoice.type',
        'invoice_type')
    def on_change_product(self):
        super().on_change_product()
        if not self.product:
            return
        if self.invoice and self.invoice.type:
            type_ = self.invoice.type
        else:
            type_ = self.invoice_type
        if type_ != 'in':
            return
        self.ganancias_regimen = self.product.ganancias_regimen_used
