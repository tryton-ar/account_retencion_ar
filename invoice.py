# This file is part of the account_retencion_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal

from trytond.model import fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval
from trytond.exceptions import UserError
from trytond.i18n import gettext


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    @fields.depends('type')
    def _get_taxes(self):
        taxes = super()._get_taxes()
        if self.type == 'out':
            taxes.update(self._get_perceptions())
        return taxes

    def _get_perceptions(self):
        taxes = {}
        if self.company.iibb_agente_percepcion:
            taxes.update(self._get_perception_iibb())
        return taxes

    def _get_perception_iibb(self):
        taxes = {}
        quantize = Decimal(10) ** -Decimal(2)

        untaxed_amount = Decimal(0)
        if self.lines:
            for line in self.lines:
                untaxed_amount += getattr(line, 'amount', None) or 0
        if not untaxed_amount:
            return taxes

        perception_data = self._get_perception_data_iibb()
        for data in perception_data.values():

            tax = data['tax']

            minimum_non_taxable_amount = (
                tax.minimum_non_taxable_amount or Decimal(0))
            if untaxed_amount < minimum_non_taxable_amount:
                continue

            taxable_amount = untaxed_amount - minimum_non_taxable_amount
            rate = data['rate']
            if not rate:
                continue

            computed_amount = taxable_amount * rate / Decimal(100)
            computed_amount = computed_amount.quantize(quantize)

            minimum_perceivable_amount = (
                tax.minimum_perceivable_amount or Decimal(0))
            if computed_amount < minimum_perceivable_amount:
                continue

            base = untaxed_amount
            amount = computed_amount
            taxline = self._compute_tax_line(amount, base, tax)
            if taxline not in taxes:
                taxes[taxline] = taxline
            else:
                taxes[taxline]['base'] += taxline['base']
                taxes[taxline]['amount'] += taxline['amount']

        return taxes

    def _get_perception_data_iibb(self):
        # Verify conditions
        if not self.party.iibb_condition:
            raise UserError(gettext(
                'account_retencion_ar.msg_party_iibb_condition'))
        if self.party.iibb_condition in ['ex', 'rs', 'na', 'cs']:
            return {}
        if self.party.iva_condition not in ['responsable_inscripto', 'exento']:
            return {}
        company_address = self.company.party.address_get('invoice')
        if not company_address or not company_address.subdivision:
            raise UserError(gettext(
                'account_retencion_ar.msg_company_subdivision'))
        company_subdivision = company_address.subdivision

        res = {}
        for tax in self.company.iibb_regimenes_percepcion:
            ok = False
            if tax.subdivision == company_subdivision:
                ok = True
            elif self.party.iibb_condition == 'cm':
                for x in self.party.iibb_regimenes:
                    if x.regimen_percepcion == tax:
                        ok = True
            if not ok:
                continue
            res[tax.id] = {
                'tax': tax,
                }

        # Verify exemptions
        taxes = [x for x in res.keys()]
        for exemption in self.party.exemptions:
            for tax_id in taxes:
                reference = 'account.tax,%s' % str(tax_id)
                if (str(exemption.tax) == reference and
                        exemption.end_date >= self.tax_date):
                    del res[tax_id]

        # Rate and extra data
        for tax_id, tax in res.items():
            tax.update(self._get_perception_extra_data_iibb(tax))

        return res

    def _get_perception_extra_data_iibb(self, tax_data):
        res = {
            'rate': Decimal(0),
            }
        regimen = tax_data['tax']
        for x in self.party.iibb_regimenes:
            if x.regimen_percepcion == regimen and x.rate_percepcion:
                res['rate'] = x.rate_percepcion
                return res
        if self.party.iibb_condition in ['in', 'cm']:
            res['rate'] = regimen.rate_registered
        else:
            res['rate'] = regimen.rate_non_registered
        return res


class InvoiceLine(metaclass=PoolMeta):
    __name__ = 'account.invoice.line'

    ganancias_regimen = fields.Many2One('account.retencion',
        'Régimen Ganancias',
        domain=[('type', '=', 'efectuada'), ('tax', '=', 'gana')],
        states={'invisible': Eval('invoice_type') != 'in'},
        context={'company': Eval('company', -1)}, depends={'company'})

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
