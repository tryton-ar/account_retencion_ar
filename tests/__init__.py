try:
    from trytond.modules.account_retencion_ar.tests.tests import suite
except ImportError:
    from .tests import suite

__all__ = ['suite']
