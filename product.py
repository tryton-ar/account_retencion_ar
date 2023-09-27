# This file is part of the account_retencion_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import fields
from trytond.pool import PoolMeta


class Category(metaclass=PoolMeta):
    __name__ = 'product.category'

    ganancias_regimen = fields.Many2One('account.retencion',
        'Régimen de Ganancias',
        domain=[('type', '=', 'efectuada'), ('tax', '=', 'gana')])


class Product(metaclass=PoolMeta):
    __name__ = 'product.product'

    ganancias_regimen_used = fields.Function(fields.Many2One(
        'account.retencion', 'Régimen Ganancias'),
        'get_ganancias_regimen_used')

    def get_ganancias_regimen_used(self, name):
        if self.account_category:
            if self.account_category.ganancias_regimen:
                return self.account_category.ganancias_regimen.id
