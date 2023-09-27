# This file is part of the account_retencion_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, fields
from trytond.pool import PoolMeta
from trytond.pyson import Eval


class Company(metaclass=PoolMeta):
    __name__ = 'company.company'

    ganancias_agente_retencion = fields.Boolean(
        'Agente de Retención de Impuesto a las Ganancias')
    ganancias_regimen_retencion = fields.Many2One('account.retencion',
        'Régimen de Ganancias',
        domain=[('type', '=', 'efectuada'), ('tax', '=', 'gana')])
    iibb_agente_retencion = fields.Boolean(
        'Agente de Retención de Impuesto a los Ingresos Brutos')
    iibb_regimenes_retencion = fields.Many2Many('company.retencion.iibb',
        'company', 'regimen', 'Jurisdicciones de Ingresos Brutos',
        domain=[('type', '=', 'efectuada'), ('tax', '=', 'iibb')])


class CompanyWithholdingIIBB(ModelSQL):
    'Régimen de Ingresos Brutos de Empresa'
    __name__ = 'company.retencion.iibb'

    company = fields.Many2One('company.company', 'Company',
        ondelete='CASCADE', required=True)
    regimen = fields.Many2One('account.retencion', 'Régimen',
        ondelete='CASCADE', required=True)
