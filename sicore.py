# -*- coding: utf-8 -*-
# This file is part of the account_retencion_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
import stdnum.ar.cuit as cuit

from trytond.model import fields, ModelView
from trytond.wizard import Wizard, StateView, StateTransition, Button
from trytond.pool import Pool

import logging
logger = logging.getLogger(__name__)


class SICORE(object):
    _EOL = '\r\n'

    def __init__(self):
        super(SICORE, self).__init__()
        self.cod_comprobante = None
        self.fecha_comprobante = None
        self.nro_comprobante = None
        self.importe_comprobante = None
        self.cod_impuesto = None
        self.cod_regimen = None
        self.cod_operacion = None
        self.base_calculo = None
        self.fecha_retencion = None
        self.cod_condicion = None
        self.suspendidos = None
        self.importe_retencion = None
        self.porcentaje_exclusion = None
        self.fecha_vigencia = None
        self.tipo_doc_retenido = None
        self.nro_doc_retenido = None
        self.nro_certificado = None

    def ordered_fields(self):
        return [
            self.cod_comprobante,
            self.fecha_comprobante,
            self.nro_comprobante,
            self.importe_comprobante,
            self.cod_impuesto,
            self.cod_regimen,
            self.cod_operacion,
            self.base_calculo,
            self.fecha_retencion,
            self.cod_condicion,
            self.suspendidos,
            self.importe_retencion,
            self.porcentaje_exclusion,
            self.fecha_vigencia,
            self.tipo_doc_retenido,
            self.nro_doc_retenido,
            self.nro_certificado,
            ]

    def _format_string(self, value, length, fillchar=' '):
        res = str(value).strip().ljust(length, fillchar)[:length]
        return res

    def _format_integer(self, value, length, fillchar='0'):
        if value == '':
            value = 0
        number = str(int(value))

        res = number.rjust(length, fillchar)[:length]
        return res

    def _format_float(self, value, int_length, dec_length=2):
        if value == '':
            value = 0
        number = str(float(value))

        int_part = int(float(number))
        dec_part = number[number.find('.') + 1:]

        res = ''
        if int_length > 0:
            res += '%.*d' % (int_length, abs(int_part))
        if dec_length > 0:
            res += (',' + str(dec_part) + '0' *
                (dec_length - len(str(dec_part))))
        return res

    def _format_date(self, value, style='%d/%m/%Y'):
        if not value:
            return '00/00/0000'
        return value.strftime(style)

    def _format_vat_number(self, vat_number, check=True):
        if not vat_number:
            return False
        if check and not self._check_vat_number(vat_number):
            return False
        vat_number = '-'.join([vat_number[:2], vat_number[2:-1],
            vat_number[-1]])
        return vat_number

    def _check_vat_number(self, vat_number):
        if (vat_number.isdigit() and
                len(vat_number) == 11 and
                cuit.is_valid(vat_number)):
            return True
        return False

    def a_text(self, csv_format=False):
        fields = self.ordered_fields()
        fields = [x for x in fields if x != '']
        separator = csv_format and ';' or ''
        text = separator.join(fields) + self._EOL
        return text

    def get_codigo_impuesto(self, retencion):
        selection = {
            'gana': 217,  # Impuesto a las Ganancias
            'bien': 219,  # Impuesto sobre Bienes Personales
            'iva': 767,   # Impuesto al Valor Agregado
            }
        return selection[retencion.tax.tax]

    def get_condicion(self, retencion):
        if retencion.tax.tax == 'gana':
            if retencion.party.ganancias_condition == 'in':
                return '01'
            return '02'
        if retencion.tax.tax == 'iva':
            return retencion.party.iva_inscripto and '01' or '02'
        if retencion.tax.tax == 'bien':
            return retencion.party.bienes_inscripto and '01' or '02'
        return '00'

    def get_comprobante(self, retencion):
        pool = Pool()
        Invoice = pool.get('account.invoice')

        voucher = retencion.voucher
        if not voucher:
            return None

        comprobante = {
            'codigo': 6,
            'fecha': voucher.date,
            'numero': voucher.number,
            'importe': voucher.amount,
            }

        # Orden de Pago como comprobante origen
        if True:
            return comprobante

        # Factura como comprobante origen
        if not voucher.lines:
            return comprobante
        for line in voucher.lines:
            if not line.move_line:
                continue
            invoices = Invoice.search([
                ('move', '=', line.move_line.move.id)])
            if not invoices:
                continue
            invoice = invoices[0]
            comprobante = {
                'codigo': 1,
                'fecha': invoice.invoice_date,
                'numero': invoice.reference,
                'importe': invoice.untaxed_amount,
                }
            return comprobante
        return comprobante


class ExportSICOREStart(ModelView):
    'Retenciones y Percepciones SICORE'
    __name__ = 'account.sicore.start'

    start_date = fields.Date('Start date', required=True)
    end_date = fields.Date('End date', required=True)
    csv_format = fields.Boolean('CSV format',
        help='Check this box if you want export to csv format.')
    regimenes_retencion = fields.Many2Many('account.retencion',
        None, None, 'Regímenes',
        domain=[('type', '=', 'efectuada'), ('tax', 'in', ['iva', 'gana'])])


class ExportSICOREResult(ModelView):
    'Retenciones y Percepciones SICORE'
    __name__ = 'account.sicore.result'

    file_ = fields.Binary('File', filename='file_name', readonly=True)
    file_name = fields.Char('Name')
    message = fields.Text('Message', readonly=True)


class ExportSICORE(Wizard):
    'Retenciones y Percepciones SICORE'
    __name__ = 'account.sicore'

    start = StateView('account.sicore.start',
        'account_retencion_ar.sicore_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Export', 'export', 'tryton-forward', default=True),
            ])
    export = StateTransition()
    result = StateView('account.sicore.result',
        'account_retencion_ar.sicore_result_view_form', [
            Button('Close', 'end', 'tryton-close', default=True),
            ])

    def transition_export(self):
        pool = Pool()
        TaxWithholdingSubmitted = pool.get('account.retencion.efectuada')

        file_contents = ''
        self.result.message = ''

        retenciones = TaxWithholdingSubmitted.search([
            ('tax', 'in', [t.id for t in self.start.regimenes_retencion]),
            ('date', '>=', self.start.start_date),
            ('date', '<=', self.start.end_date),
            ('state', '=', 'issued'),
            ], order=[
            ('date', 'ASC'),
            ('name', 'ASC'),
            ])
        for retencion in retenciones:
            aux_record, add_line, message = self._format_retencion(retencion)
            if add_line:
                file_contents += aux_record
            if message:
                self.result.message += message + '\n'

        self.result.file_ = str(file_contents).encode('utf-8')
        return 'result'

    def _format_retencion(self, retencion):
        Cbte = SICORE()

        comprobante = Cbte.get_comprobante(retencion)
        if not comprobante:
            return ('', False, 'ERROR: La retencion %s no tiene un comprobante'
                ' asociado. Fue quitada del listado.'
                % (retencion.name,))

        Cbte.cod_comprobante = Cbte._format_integer(
            comprobante['codigo'], 2)
        Cbte.fecha_comprobante = Cbte._format_date(
            comprobante['fecha'])
        Cbte.nro_comprobante = Cbte._format_string(
            comprobante['numero'], 16)
        Cbte.importe_comprobante = Cbte._format_float(
            comprobante['importe'], 13, 2)
        Cbte.cod_impuesto = Cbte._format_integer(
            Cbte.get_codigo_impuesto(retencion), 4)
        Cbte.cod_regimen = Cbte._format_integer(
            retencion.regime_code, 3)
        Cbte.cod_operacion = '1'  # Retención
        Cbte.base_calculo = Cbte._format_float(
            retencion.payment_amount or 0, 11, 2)
        Cbte.fecha_retencion = Cbte._format_date(
            retencion.date)
        Cbte.cod_condicion = Cbte.get_condicion(retencion)
        Cbte.suspendidos = '0'
        Cbte.importe_retencion = Cbte._format_float(
            retencion.amount, 11, 2)
        Cbte.porcentaje_exclusion = Cbte._format_float(
            0, 3, 2)
        Cbte.fecha_vigencia = '00/00/0000'
        Cbte.tipo_doc_retenido = Cbte._format_integer(
            retencion.party.tipo_documento, 2)
        Cbte.nro_doc_retenido = Cbte._format_string(
            retencion.party.vat_number, 20)
        Cbte.nro_certificado = Cbte._format_integer(
            0, 14)
        #Cbte.nro_certificado = Cbte._format_string(
            #retencion.name, 14)

        return (Cbte.a_text(self.start.csv_format), True, '')

    def default_result(self, fields):
        file_ = self.result.file_
        message = self.result.message
        file_name = 'SICORE_%s-%s.%s' % (
            self.start.start_date.strftime('%Y%m%d'),
            self.start.end_date.strftime('%Y%m%d'),
            'csv' if self.start.csv_format else 'txt')

        self.result.file_ = None
        self.result.message = None

        return {
            'file_': file_,
            'file_name': file_name,
            'message': message,
            }
