# This file is part of the account_retencion_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import account_retencion_ar
from . import account_voucher_ar
from . import party
from . import company
from . import product


def register():
    Pool.register(
        account_retencion_ar.TaxWithholdingType,
        account_retencion_ar.TaxWithholdingTypeSequence,
        account_retencion_ar.TaxWithholdingTypeScale,
        account_retencion_ar.TaxWithholdingSubmitted,
        account_retencion_ar.TaxWithholdingReceived,
        account_voucher_ar.AccountVoucher,
        account_voucher_ar.RecalculateWithholdingsStart,
        party.Party,
        party.PartyExemption,
        party.PartyWithholdingIIBB,
        company.Company,
        company.CompanyWithholdingIIBB,
        product.Category,
        product.Product,
        invoice.InvoiceLine,
        module='account_retencion_ar', type_='model')
    Pool.register(
        account_voucher_ar.RecalculateWithholdings,
        module='account_retencion_ar', type_='wizard')
