# This file is part of the account_retencion_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import account_retencion_ar
from . import account_voucher_ar


def register():
    Pool.register(
        account_retencion_ar.AccountRetencion,
        account_retencion_ar.AccountRetencionSequence,
        account_retencion_ar.AccountRetencionEfectuada,
        account_retencion_ar.AccountRetencionSoportada,
        account_voucher_ar.AccountVoucher,
        module='account_retencion_ar', type_='model')
