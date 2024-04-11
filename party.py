# This file is part of the account_retencion_ar module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.

from trytond.model import ModelSQL, ModelView, fields
from trytond.pool import PoolMeta


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    exemptions = fields.One2Many('party.exemption',
        'party', 'Exenciones de Retención y Percepción')
    ganancias_regimen = fields.Many2One('account.retencion',
        'Régimen de Ganancias',
        domain=[('type', '=', 'efectuada'), ('tax', '=', 'gana')])
    iva_regimen = fields.Many2One('account.retencion',
        'Régimen de IVA',
        domain=[('type', '=', 'efectuada'), ('tax', '=', 'iva')])
    iibb_regimenes = fields.One2Many('party.retencion.iibb',
        'party', 'Jurisdicciones de Ingresos Brutos')


class PartyExemption(ModelSQL, ModelView):
    'Exención de Retención/Percepción de Tercero'
    __name__ = 'party.exemption'

    party = fields.Many2One('party.party', 'Party',
        ondelete='CASCADE', required=True)
    tax = fields.Reference('Type', [
            ('account.retencion', 'Retención'),
            ('account.tax', 'Percepción'),
            ],
        required=True,
        domain={
            'account.retencion': [
                ('type', '=', 'efectuada')
                ],
            'account.tax': [
                ('group.afip_kind', 'in',
                    ['nacional', 'provincial', 'municipal']),
                ('group.kind', '=', 'sale'),
                ],
            })
    end_date = fields.Date('Valid until', required=True)


class PartyWithholdingIIBB(ModelSQL, ModelView):
    'Régimen de Ingresos Brutos de Tercero'
    __name__ = 'party.retencion.iibb'

    party = fields.Many2One('party.party', 'Party',
        ondelete='CASCADE', required=True)
    regimen_retencion = fields.Many2One('account.retencion',
        'Retención', ondelete='CASCADE',
        domain=[('type', '=', 'efectuada'), ('tax', '=', 'iibb')])
    rate_retencion = fields.Numeric('% Retención', digits=(14, 10))
    regimen_percepcion = fields.Many2One('account.tax',
        'Percepción', ondelete='CASCADE',
        domain=[
            ('group.afip_kind', '=', 'provincial'),
            ('perception_tax_code', '=', 'iibb'),
            ('group.kind', '=', 'sale'),
            ])
    rate_percepcion = fields.Numeric('% Percepción', digits=(14, 10))
