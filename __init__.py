#This file is part of the account_retencion_ar module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.


from trytond.pool import Pool
from .account_retencion_ar import *
from .account_voucher_ar import *


def register():
    Pool.register(
        AccountRetencion,
        AccountRetencionEfectuada,
        AccountRetencionSoportada,
        AccountVoucher,
        module='account_retencion_ar', type_='model')

