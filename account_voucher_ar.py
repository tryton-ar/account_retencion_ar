# This file is part of the account_retencion_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from trytond.model import Workflow, ModelView, fields
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, Or, And
from trytond.transaction import Transaction
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

    @classmethod
    def __setup__(cls):
        super().__setup__()
        calculated_state = ('calculated', 'Calculated')
        if calculated_state not in cls.state.selection:
            cls.state.selection.append(calculated_state)
        cls._transitions |= set((
            ('draft', 'calculated'),
            ('calculated', 'draft'),
            ('calculated', 'posted'),
            ))
        cls._buttons.update({
            'calculate': {
                'invisible': Or(
                    Eval('voucher_type') != 'payment',
                    Eval('state') != 'draft'),
                'depends': ['voucher_type', 'state'],
                },
            'recalculate': {
                'invisible': And(
                    Eval('state') != 'calculated',
                    Eval('amount_to_pay', 0) > Eval('amount', 0)),
                'depends': ['state', 'amount_to_pay', 'amount'],
                },
            'draft': {
                'invisible': Eval('state') != 'calculated',
                'depends': ['state'],
                },
            'post': {
                'invisible': Or(
                    And(Eval('voucher_type') == 'payment',
                        Eval('state') != 'calculated'),
                    And(Eval('voucher_type') == 'receipt',
                        Eval('state') != 'draft')),
                'depends': ['voucher_type', 'state'],
                },
            'cancel': {
                'invisible': Eval('state') != 'posted',
                'depends': ['state'],
                },
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

    @classmethod
    @ModelView.button
    @Workflow.transition('draft')
    def draft(cls, vouchers):
        for voucher in vouchers:
            voucher.delete_withholding()

    def delete_withholding(self):
        pool = Pool()
        TaxWithholdingSubmitted = pool.get('account.retencion.efectuada')
        if self.retenciones_efectuadas:
            with Transaction().set_context(delete_calculated=True):
                TaxWithholdingSubmitted.delete(self.retenciones_efectuadas)

    @classmethod
    @ModelView.button
    @Workflow.transition('calculated')
    def calculate(cls, vouchers):
        for voucher in vouchers:
            voucher.calculate_withholdings()

    @classmethod
    @ModelView.button_action(
        'account_retencion_ar.wizard_recalculate_withholdings')
    def recalculate(cls, vouchers):
        pass

    def calculate_withholdings(self, context={}):
        if self.company.ganancias_agente_retencion:
            self._calculate_withholding_ganancias(context)
        if self.company.iibb_agente_retencion:
            self._calculate_withholding_iibb(context)

    def _calculate_withholding_ganancias(self, context={}):
        pool = Pool()
        TaxWithholdingSubmitted = pool.get('account.retencion.efectuada')

        quantize = Decimal(10) ** -Decimal(2)

        withholding_data = self._get_withholding_data_ganancias(context)
        for data in withholding_data.values():

            withholding_type = data['tax']

            payment_amount = data['payment_amount']
            accumulated_amount = data['accumulated_amount'] + payment_amount
            minimum_non_taxable_amount = (
                withholding_type.minimum_non_taxable_amount or Decimal(0))
            if accumulated_amount < minimum_non_taxable_amount:
                continue

            taxable_amount = accumulated_amount - minimum_non_taxable_amount
            rate = data['rate']
            if not rate:
                continue

            scale_non_taxable_amount = data['scale_non_taxable_amount']
            computed_amount = ((taxable_amount - scale_non_taxable_amount) *
                rate / Decimal(100))
            computed_amount = computed_amount.quantize(quantize)

            scale_fixed_amount = data['scale_fixed_amount']
            computed_amount += scale_fixed_amount

            minimum_withholdable_amount = (
                withholding_type.minimum_withholdable_amount or Decimal(0))
            if computed_amount < minimum_withholdable_amount:
                continue

            accumulated_withheld = data['accumulated_withheld']
            amount = computed_amount - accumulated_withheld

            withholding = TaxWithholdingSubmitted()
            withholding.tax = withholding_type
            withholding.voucher = self
            withholding.party = self.party
            withholding.date = self.date
            withholding.payment_amount = payment_amount
            withholding.accumulated_amount = accumulated_amount
            withholding.minimum_non_taxable_amount = minimum_non_taxable_amount
            withholding.scale_non_taxable_amount = scale_non_taxable_amount
            withholding.taxable_amount = taxable_amount
            withholding.rate = rate
            withholding.scale_fixed_amount = scale_fixed_amount
            withholding.computed_amount = computed_amount
            withholding.minimum_withholdable_amount = (
                minimum_withholdable_amount)
            withholding.accumulated_withheld = accumulated_withheld
            withholding.amount = amount
            withholding.save()

    def _get_withholding_data_ganancias(self, context={}):
        pool = Pool()
        Invoice = pool.get('account.invoice')
        AccountVoucher = pool.get('account.voucher')
        TaxWithholdingSubmitted = pool.get('account.retencion.efectuada')

        # Verify conditions
        if not self.party.ganancias_condition:
            raise UserError(gettext(
                'account_retencion_ar.msg_party_ganancias_condition'))
        if self.party.ganancias_condition == 'ex':
            return {}

        quantize = Decimal(10) ** -Decimal(2)
        res = {}

        default_regimen = self.party.ganancias_regimen
        if not default_regimen:
            default_regimen = self.company.ganancias_regimen_retencion
        if not default_regimen:
            return {}

        # Payment Amount
        vat_rate = context.get('vat_rate', Decimal(0.21))
        if context:
            amount = context.get('amount', Decimal(0))
            amount_option = context.get('amount_option', 'add')

            if amount_option == 'add':
                tax = default_regimen
                if tax.id not in res:
                    res[tax.id] = {
                        'tax': tax,
                        'payment_amount': Decimal(0),
                        'accumulated_amount': Decimal(0),
                        'accumulated_withheld': Decimal(0),
                        }
                payment_amount = amount / (1 + vat_rate)
                res[tax.id]['payment_amount'] += (
                    payment_amount.quantize(quantize))

            else:  # amount_option == 'included'
                pass

        else:
            for line in self.lines:
                origin = str(line.move_line.move_origin)
                if origin[:origin.find(',')] != 'account.invoice':
                    continue
                if not line.amount:
                    continue

                invoice = Invoice(line.move_line.move_origin.id)
                payment_rate = Decimal(line.amount / invoice.total_amount)

                for invoice_line in invoice.lines:
                    if invoice_line.type != 'line':
                        continue
                    tax = invoice_line.ganancias_regimen or default_regimen
                    if tax.id not in res:
                        res[tax.id] = {
                            'tax': tax,
                            'payment_amount': Decimal(0),
                            'accumulated_amount': Decimal(0),
                            'accumulated_withheld': Decimal(0),
                            }
                    payment_amount = invoice_line.amount * payment_rate
                    res[tax.id]['payment_amount'] += (
                        payment_amount.quantize(quantize))

        # Verify exemptions
        taxes = [x for x in res.keys()]
        for exemption in self.party.exemptions:
            for tax_id in taxes:
                reference = 'account.retencion,%s' % str(tax_id)
                if (str(exemption.tax) == reference and
                        exemption.end_date >= self.date):
                    del res[tax_id]

        # Accumulated Amount
        period_first_date = self.date + relativedelta(day=1)
        period_last_date = self.date + relativedelta(day=31)
        vouchers = AccountVoucher.search([
            ('party', '=', self.party),
            ('date', '>=', period_first_date),
            ('date', '<=', period_last_date),
            ('state', '=', 'posted'),
            ])
        for voucher in vouchers:
            for line in voucher.lines:
                origin = str(line.move_line.move_origin)
                if origin[:origin.find(',')] != 'account.invoice':
                    continue
                if not line.amount:
                    continue

                invoice = Invoice(line.move_line.move_origin.id)
                payment_rate = Decimal(line.amount / invoice.total_amount)

                for invoice_line in invoice.lines:
                    if invoice_line.type != 'line':
                        continue
                    tax = invoice_line.ganancias_regimen or default_regimen
                    if tax.id not in res:
                        continue
                    accumulated_amount = invoice_line.amount * payment_rate
                    res[tax.id]['accumulated_amount'] += (
                        accumulated_amount.quantize(quantize))

            if voucher.amount > voucher.amount_to_pay:
                difference = ((voucher.amount - voucher.amount_to_pay) /
                    (1 + vat_rate))
                if default_regimen.id in res:
                    res[default_regimen.id]['accumulated_amount'] += (
                        difference.quantize(quantize))

        # Accumulated Withheld
        for tax_id in res.keys():
            withholdings = TaxWithholdingSubmitted.search([
                ('tax', '=', tax_id),
                ('party', '=', self.party),
                ('date', '>=', period_first_date),
                ('date', '<=', period_last_date),
                ('state', '=', 'issued'),
                ])
            for withholding in withholdings:
                res[tax_id]['accumulated_withheld'] += withholding.amount

        # Rate and extra data
        for tax_id, tax in res.items():
            tax.update(self._get_withholding_extra_data_ganancias(tax))

        return res

    def _get_withholding_extra_data_ganancias(self, tax_data):
        res = {
            'rate': Decimal(0),
            'scale_non_taxable_amount': Decimal(0),
            'scale_fixed_amount': Decimal(0),
            }
        regimen = tax_data['tax']
        if regimen.scales:
            taxable_amount = (tax_data['payment_amount'] +
                tax_data['accumulated_amount'] -
                regimen.minimum_non_taxable_amount)
            for scale in regimen.scales:
                if (taxable_amount >= scale.start_amount and
                        taxable_amount <= scale.end_amount):
                    res['rate'] = scale.rate
                    res['scale_non_taxable_amount'] = (
                        scale.minimum_non_taxable_amount)
                    res['scale_fixed_amount'] = (
                        scale.fixed_withholdable_amount)
                    return res
        if self.party.ganancias_condition == 'in':
            res['rate'] = regimen.rate_registered
        else:
            res['rate'] = regimen.rate_non_registered
        return res

    def _calculate_withholding_iibb(self, context={}):
        pool = Pool()
        TaxWithholdingSubmitted = pool.get('account.retencion.efectuada')

        quantize = Decimal(10) ** -Decimal(2)

        withholding_data = self._get_withholding_data_iibb(context)
        for data in withholding_data.values():

            withholding_type = data['tax']

            payment_amount = data['payment_amount']
            accumulated_amount = data['accumulated_amount'] + payment_amount
            minimum_non_taxable_amount = (
                withholding_type.minimum_non_taxable_amount or Decimal(0))
            if accumulated_amount < minimum_non_taxable_amount:
                continue

            taxable_amount = accumulated_amount - minimum_non_taxable_amount
            rate = data['rate']
            if not rate:
                continue

            computed_amount = taxable_amount * rate / Decimal(100)
            computed_amount = computed_amount.quantize(quantize)

            minimum_withholdable_amount = (
                withholding_type.minimum_withholdable_amount or Decimal(0))
            if computed_amount < minimum_withholdable_amount:
                continue

            accumulated_withheld = data['accumulated_withheld']
            amount = computed_amount - accumulated_withheld

            withholding = TaxWithholdingSubmitted()
            withholding.tax = withholding_type
            withholding.voucher = self
            withholding.party = self.party
            withholding.date = self.date
            withholding.payment_amount = payment_amount
            withholding.accumulated_amount = accumulated_amount
            withholding.minimum_non_taxable_amount = minimum_non_taxable_amount
            withholding.taxable_amount = taxable_amount
            withholding.rate = rate
            withholding.computed_amount = computed_amount
            withholding.minimum_withholdable_amount = (
                minimum_withholdable_amount)
            withholding.accumulated_withheld = accumulated_withheld
            withholding.amount = amount
            withholding.save()

    def _get_withholding_data_iibb(self, context={}):
        pool = Pool()
        Invoice = pool.get('account.invoice')

        # Verify conditions
        if not self.party.iibb_condition:
            raise UserError(gettext(
                'account_retencion_ar.msg_party_iibb_condition'))
        if self.party.iibb_condition in ['ex', 'rs', 'na', 'cs']:
            return {}
        company_address = self.company.party.address_get('invoice')
        if not company_address or not company_address.subdivision:
            raise UserError(gettext(
                'account_retencion_ar.msg_company_subdivision'))
        company_subdivision = company_address.subdivision

        quantize = Decimal(10) ** -Decimal(2)
        res = {}

        vat_rate = context.get('vat_rate', Decimal(0.21))
        if context:
            amount = context.get('amount', Decimal(0))
            amount_option = context.get('amount_option', 'add')

        for tax in self.company.iibb_regimenes_retencion:
            ok = False
            if tax.subdivision == company_subdivision:
                ok = True
            elif self.party.iibb_condition == 'cm':
                for x in self.party.iibb_regimenes:
                    if x.regimen_retencion == tax:
                        ok = True
            if not ok:
                continue

            # Payment Amount
            if context:
                if amount_option == 'add':
                    if tax.id not in res:
                        res[tax.id] = {
                            'tax': tax,
                            'payment_amount': Decimal(0),
                            'accumulated_amount': Decimal(0),
                            'accumulated_withheld': Decimal(0),
                            }
                    payment_amount = amount / (1 + vat_rate)
                    res[tax.id]['payment_amount'] += (
                        payment_amount.quantize(quantize))

                else:  # amount_option == 'included'
                    pass

            else:
                for line in self.lines:
                    origin = str(line.move_line.move_origin)
                    if origin[:origin.find(',')] != 'account.invoice':
                        continue
                    if not line.amount:
                        continue

                    if tax.id not in res:
                        res[tax.id] = {
                            'tax': tax,
                            'payment_amount': Decimal(0),
                            'accumulated_amount': Decimal(0),
                            'accumulated_withheld': Decimal(0),
                            }

                    invoice = Invoice(line.move_line.move_origin.id)
                    if line.amount == invoice.total_amount:
                        payment_amount = invoice.untaxed_amount
                    else:
                        payment_amount = (line.amount *
                            invoice.untaxed_amount / invoice.total_amount)
                    res[tax.id]['payment_amount'] += payment_amount.quantize(
                        quantize)

        # Verify exemptions
        taxes = [x for x in res.keys()]
        for exemption in self.party.exemptions:
            for tax_id in taxes:
                reference = 'account.retencion,%s' % str(tax_id)
                if (str(exemption.tax) == reference and
                        exemption.end_date >= self.date):
                    del res[tax_id]

        # Rate and extra data
        for tax_id, tax in res.items():
            tax.update(self._get_withholding_extra_data_iibb(tax))

        return res

    def _get_withholding_extra_data_iibb(self, tax_data):
        res = {
            'rate': Decimal(0),
            }
        regimen = tax_data['tax']
        for x in self.party.iibb_regimenes:
            if x.regimen_retencion == regimen and x.rate_retencion:
                res['rate'] = x.rate_retencion
                return res
        if self.party.iibb_condition in ['in', 'cm']:
            res['rate'] = regimen.rate_registered
        else:
            res['rate'] = regimen.rate_non_registered
        return res

    def prepare_move_lines(self):
        pool = Pool()
        Period = pool.get('account.period')

        move_lines = super().prepare_move_lines()

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


class RecalculateWithholdingsStart(ModelView):
    'Recalculate withholdings'
    __name__ = 'account.voucher.recalculate_withholdings.start'

    amount = fields.Numeric('Payment Amount', digits=(16, 2), required=True)
    amount_option = fields.Selection([
        ('add', 'Add withholdings to the amount'),
        #('included', 'Withholdings included in the amount'),
        ], 'Option', required=True, sort=False)

    @staticmethod
    def default_amount_option():
        return 'add'


class RecalculateWithholdings(Wizard):
    'Recalculate withholdings'
    __name__ = 'account.voucher.recalculate_withholdings'

    start = StateView(
        'account.voucher.recalculate_withholdings.start',
        'account_retencion_ar.recalculate_withholdings_start_view', [
            Button('Cancelar', 'end', 'tryton-cancel'),
            Button('Recalculate', 'recalculate', 'tryton-ok', default=True),
        ])
    recalculate = StateTransition()

    def transition_recalculate(self):
        AccountVoucher = Pool().get('account.voucher')

        voucher = AccountVoucher(Transaction().context['active_id'])
        if not voucher:
            return {}

        voucher.delete_withholding()
        voucher.calculate_withholdings(context={
            'amount': self.start.amount,
            'vat_rate': Decimal(0.21),
            'amount_option': self.start.amount_option,
            })
        return 'end'

    def end(self):
        return 'reload'
