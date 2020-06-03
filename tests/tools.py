# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from proteus import Model
from trytond.modules.company.tests.tools import get_company

__all__ = ['create_retencion_sequence']


def create_retencion_sequence(company=None, config=None):
    "Create retencion sequence"
    Sequence = Model.get('ir.sequence', config=config)

    if not company:
        company = get_company()

    retencion_seq = Sequence(name='retencion', code='account.retencion',
        company=company)
    retencion_seq.save()
    return retencion_seq
