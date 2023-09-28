==========================
Account Retencion Scenario
==========================

Imports::
    >>> import datetime
    >>> from dateutil.relativedelta import relativedelta
    >>> from decimal import Decimal
    >>> from operator import attrgetter
    >>> from proteus import Model, Wizard
    >>> from trytond.tests.tools import activate_modules
    >>> from trytond.modules.company.tests.tools import create_company, \
    ...     get_company
    >>> from trytond.modules.currency.tests.tools import get_currency
    >>> from trytond.modules.account.tests.tools import create_fiscalyear, \
    ...     create_chart, get_accounts, create_tax, create_tax_code
    >>> from trytond.modules.account_invoice.tests.tools import \
    ...     set_fiscalyear_invoice_sequences
    >>> from trytond.modules.account_voucher_ar.tests.tools import \
    ...     set_fiscalyear_voucher_sequences
    >>> from trytond.modules.account_retencion_ar.tests.tools import \
    ...     create_retencion_sequence
    >>> today = datetime.date.today()

Install account_invoice::

    >>> config = activate_modules('account_retencion_ar')

Create company::

    >>> currency = get_currency('ARS')
    >>> _ = create_company(currency=currency)
    >>> company = get_company()
    >>> tax_identifier = company.party.identifiers.new()
    >>> tax_identifier.type = 'ar_cuit'
    >>> tax_identifier.code = '30710158254' # gcoop CUIT
    >>> company.party.iva_condition = 'responsable_inscripto'
    >>> company.party.save()

Create fiscal year::

    >>> fiscalyear = set_fiscalyear_voucher_sequences(
    ...     set_fiscalyear_invoice_sequences(
    ...     create_fiscalyear(company)))
    >>> fiscalyear.click('create_period')
    >>> period = fiscalyear.periods[0]
    >>> period_ids = [p.id for p in fiscalyear.periods]

Create chart of accounts::

    >>> _ = create_chart(company)
    >>> accounts = get_accounts(company)
    >>> receivable = accounts['receivable']
    >>> revenue = accounts['revenue']
    >>> expense = accounts['expense']
    >>> account_tax = accounts['tax']
    >>> account_cash = accounts['cash']

Create tax groups::

    >>> TaxGroup = Model.get('account.tax.group')
    >>> tax_group = TaxGroup()
    >>> tax_group.name = 'gravado'
    >>> tax_group.code = 'gravado'
    >>> tax_group.kind = 'both'
    >>> tax_group.afip_kind = 'gravado'
    >>> tax_group.save()

Create tax::

    >>> TaxCode = Model.get('account.tax.code')
    >>> tax = create_tax(Decimal('.10'))
    >>> tax.group = tax_group
    >>> tax.save()
    >>> invoice_base_code = create_tax_code(tax, 'base', 'invoice')
    >>> invoice_base_code.save()
    >>> invoice_tax_code = create_tax_code(tax, 'tax', 'invoice')
    >>> invoice_tax_code.save()
    >>> credit_note_base_code = create_tax_code(tax, 'base', 'credit')
    >>> credit_note_base_code.save()
    >>> credit_note_tax_code = create_tax_code(tax, 'tax', 'credit')
    >>> credit_note_tax_code.save()

Create payment method voucher_ar::

    >>> AccountVoucherPayMode = Model.get('account.voucher.paymode')
    >>> paymode = AccountVoucherPayMode()
    >>> paymode.name = 'Cash'
    >>> paymode.account = account_cash
    >>> paymode.save()


Create payment method::

    >>> Journal = Model.get('account.journal')
    >>> PaymentMethod = Model.get('account.invoice.payment.method')
    >>> Sequence = Model.get('ir.sequence')
    >>> journal_cash, = Journal.find([('type', '=', 'cash')])
    >>> payment_method = PaymentMethod()
    >>> payment_method.name = 'Cash'
    >>> payment_method.journal = journal_cash
    >>> payment_method.credit_account = account_cash
    >>> payment_method.debit_account = account_cash
    >>> payment_method.save()

Create Write Off method::

    >>> WriteOff = Model.get('account.move.reconcile.write_off')
    >>> sequence_journal, = Sequence.find(
    ...     [('sequence_type.name', '=', "Account Journal")], limit=1)
    >>> journal_writeoff = Journal(name='Write-Off', type='write-off',
    ...     sequence=sequence_journal)
    >>> journal_writeoff.save()
    >>> writeoff_method = WriteOff()
    >>> writeoff_method.name = 'Rate loss'
    >>> writeoff_method.journal = journal_writeoff
    >>> writeoff_method.credit_account = expense
    >>> writeoff_method.debit_account = expense
    >>> writeoff_method.save()

Create party::

    >>> Party = Model.get('party.party')
    >>> party = Party(name='Party')
    >>> party.iva_condition = 'consumidor_final'
    >>> party.save()

Create account category::

    >>> ProductCategory = Model.get('product.category')
    >>> account_category = ProductCategory(name="Account Category")
    >>> account_category.accounting = True
    >>> account_category.account_expense = expense
    >>> account_category.account_revenue = revenue
    >>> account_category.customer_taxes.append(tax)
    >>> account_category.save()

Create product::

    >>> ProductUom = Model.get('product.uom')
    >>> unit, = ProductUom.find([('name', '=', 'Unit')])
    >>> ProductTemplate = Model.get('product.template')
    >>> template = ProductTemplate()
    >>> template.name = 'product'
    >>> template.default_uom = unit
    >>> template.type = 'service'
    >>> template.list_price = Decimal('40')
    >>> template.account_category = account_category
    >>> template.save()
    >>> product, = template.products

Create payment term::

    >>> PaymentTerm = Model.get('account.invoice.payment_term')
    >>> payment_term = PaymentTerm(name='Term')
    >>> line = payment_term.lines.new(type='percent', ratio=Decimal('.5'))
    >>> delta, = line.relativedeltas
    >>> delta.days = 20
    >>> line = payment_term.lines.new(type='remainder')
    >>> delta = line.relativedeltas.new(days=40)
    >>> payment_term.save()

Create Retenciones::

    >>> Retencion = Model.get('account.retencion')
    >>> retencion_soportada = Retencion(name='Retencion soportada')
    >>> retencion_soportada.account = account_tax
    >>> retencion_soportada.type = 'soportada'
    >>> retencion_soportada.tax = 'iva'
    >>> retencion_soportada.save()
    >>> retencion_efectuada = Retencion(name='Retencion efectuada')
    >>> retencion_efectuada.account = account_tax
    >>> retencion_efectuada.type = 'efectuada'
    >>> retencion_efectuada.tax = 'iva'
    >>> retencion_efectuada.sequence = create_retencion_sequence()
    >>> retencion_efectuada.save()

Create invoice::

    >>> Invoice = Model.get('account.invoice')
    >>> InvoiceLine = Model.get('account.invoice.line')
    >>> invoice = Invoice()
    >>> invoice.party = party
    >>> invoice.payment_term = payment_term
    >>> line = InvoiceLine()
    >>> invoice.lines.append(line)
    >>> line.product = product
    >>> line.quantity = 5
    >>> line.unit_price = Decimal('40')
    >>> line = InvoiceLine()
    >>> invoice.lines.append(line)
    >>> line.account = revenue
    >>> line.description = 'Test'
    >>> line.quantity = 1
    >>> line.unit_price = Decimal(20)
    >>> invoice.untaxed_amount
    Decimal('220.00')
    >>> invoice.tax_amount
    Decimal('20.00')
    >>> invoice.total_amount
    Decimal('240.00')
    >>> invoice.save()

Post invoice::

    >>> invoice.click('post')
    >>> invoice.state
    'posted'
    >>> invoice.tax_identifier.code
    '30710158254'
    >>> invoice.untaxed_amount
    Decimal('220.00')
    >>> invoice.tax_amount
    Decimal('20.00')
    >>> invoice.total_amount
    Decimal('240.00')

Pay invoice::

    >>> AccountVoucher = Model.get('account.voucher')
    >>> LinePaymode = Model.get('account.voucher.line.paymode')
    >>> RetencionSoportada = Model.get('account.retencion.soportada')
    >>> voucher = AccountVoucher()
    >>> voucher.party = invoice.party
    >>> voucher.date = today
    >>> voucher.voucher_type = 'receipt'
    >>> voucher.journal = journal_cash
    >>> voucher.currency = invoice.currency
    >>> payment_line, = voucher.lines
    >>> payment_line.amount = payment_line.amount_unreconciled
    >>> pay_line = LinePaymode()
    >>> voucher.pay_lines.append(pay_line)
    >>> pay_line.pay_mode = paymode
    >>> pay_line.pay_amount = Decimal('200')
    >>> retencion_line = RetencionSoportada()
    >>> voucher.retenciones_soportadas.append(retencion_line)
    >>> retencion_line.name = '1111'
    >>> retencion_line.amount = Decimal('40')
    >>> retencion_line.tax = retencion_soportada
    >>> retencion_line.party = invoice.party
    >>> voucher.save()
    >>> voucher.click('post')
    >>> voucher.state
    'posted'
    >>> bool(voucher.move)
    True
    >>> invoice.reload()
    >>> invoice.state
    'paid'
    >>> len(invoice.payment_lines)
    1

Create supplier invoice::

    >>> Invoice = Model.get('account.invoice')
    >>> InvoiceLine = Model.get('account.invoice.line')
    >>> invoice = Invoice()
    >>> invoice.party = party
    >>> invoice.type = 'in'
    >>> invoice.payment_term = None
    >>> invoice.invoice_date = today
    >>> line = InvoiceLine()
    >>> invoice.lines.append(line)
    >>> line.product = product
    >>> line.quantity = 5
    >>> line.unit_price = Decimal('40')
    >>> line = InvoiceLine()
    >>> invoice.lines.append(line)
    >>> line.account = expense
    >>> line.description = 'Test'
    >>> line.quantity = 1
    >>> line.unit_price = Decimal(20)
    >>> invoice.untaxed_amount
    Decimal('220.00')
    >>> invoice.total_amount
    Decimal('220.00')
    >>> invoice.save()
    >>> invoice.state
    'draft'
    >>> bool(invoice.move)
    False
    >>> invoice.click('validate_invoice')
    >>> invoice.state
    'validated'
    >>> bool(invoice.move)
    True

Post invoice::

    >>> invoice.click('post')
    >>> invoice.state
    'posted'
    >>> bool(invoice.move)
    True
    >>> invoice.move.state
    'posted'
    >>> invoice.tax_identifier.code
    '30710158254'
    >>> invoice.untaxed_amount
    Decimal('220.00')
    >>> invoice.total_amount
    Decimal('220.00')

Pay invoice::

    >>> AccountVoucher = Model.get('account.voucher')
    >>> LinePaymode = Model.get('account.voucher.line.paymode')
    >>> RetencionEfectuada = Model.get('account.retencion.efectuada')
    >>> voucher = AccountVoucher()
    >>> voucher.party = invoice.party
    >>> voucher.date = today
    >>> voucher.voucher_type = 'payment'
    >>> voucher.journal = journal_cash
    >>> voucher.currency = invoice.currency
    >>> payment_line, = voucher.lines
    >>> payment_line.amount = payment_line.amount_unreconciled
    >>> pay_line = LinePaymode()
    >>> voucher.pay_lines.append(pay_line)
    >>> pay_line.pay_mode = paymode
    >>> pay_line.pay_amount = Decimal('200')
    >>> retencion_line = RetencionEfectuada()
    >>> voucher.retenciones_efectuadas.append(retencion_line)
    >>> retencion_line.name = '1111'
    >>> retencion_line.amount = Decimal('20')
    >>> retencion_line.tax = retencion_efectuada
    >>> retencion_line.party = invoice.party
    >>> voucher.save()
    >>> voucher.click('post')
    >>> voucher.state
    'posted'
    >>> bool(voucher.move)
    True
    >>> invoice.reload()
    >>> invoice.state
    'paid'
    >>> len(invoice.payment_lines)
    1
