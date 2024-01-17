# This file is part of the account_retencion_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.pool import Pool
from . import account_retencion_ar
from . import account_voucher_ar
from . import party
from . import company
from . import product
from . import invoice
from . import sicore


def register():
    Pool.register(
        account_retencion_ar.TaxWithholdingType,
        account_retencion_ar.TaxWithholdingTypeSequence,
        account_retencion_ar.TaxWithholdingTypeScale,
        account_retencion_ar.TaxWithholdingSubmitted,
        account_retencion_ar.TaxWithholdingReceived,
        account_retencion_ar.Perception,
        account_retencion_ar.PrintIIBBSubdivisionStart,
        account_retencion_ar.PrintPerceptionBySubdivisionStart,
        account_voucher_ar.AccountVoucher,
        account_voucher_ar.RecalculateWithholdingsStart,
        party.Party,
        party.PartyExemption,
        party.PartyWithholdingIIBB,
        company.Company,
        company.CompanyWithholdingIIBB,
        company.CompanyPerceptionIIBB,
        product.Category,
        product.Product,
        invoice.Invoice,
        invoice.InvoiceLine,
        sicore.ExportSICOREStart,
        sicore.ExportSICOREResult,
        module='account_retencion_ar', type_='model')
    Pool.register(
        account_retencion_ar.PrintIIBBSubdivision,
        account_retencion_ar.PrintPerceptionBySubdivision,
        account_voucher_ar.RecalculateWithholdings,
        sicore.ExportSICORE,
        module='account_retencion_ar', type_='wizard')
    Pool.register(
        account_retencion_ar.TaxWithholdingSubmittedReport,
        account_retencion_ar.IIBBSubdivisionReport,
        account_retencion_ar.PerceptionBySubdivisionReport,
        module='account_retencion_ar', type_='report')
