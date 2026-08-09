"""Settings feature: a hub screen (Ajustes) plus one subpackage per section.

metodos_pago, reglas_cobro, reset and audit_log each get their own
subpackage (view.py plus toolbar.py/dialog.py/service.py where relevant),
keeping each section's files grouped together instead of flat-named.
"""

from .menu_view import SettingsView, show_settings_view
from .metodos_pago.view import MetodosPagoView, show_metodos_pago_view
from .metodos_pago.toolbar import MetodosPagoToolBar
from .reglas_cobro.view import ReglasCobroView, show_reglas_cobro_view
from .reglas_cobro.toolbar import ReglasCobroToolBar
from .reset.view import ResetView, show_reset_view
from .audit_log.view import AuditLogView, show_audit_log_view

__all__ = [
    "SettingsView",
    "show_settings_view",
    "MetodosPagoView",
    "show_metodos_pago_view",
    "MetodosPagoToolBar",
    "ReglasCobroView",
    "show_reglas_cobro_view",
    "ReglasCobroToolBar",
    "ResetView",
    "show_reset_view",
    "AuditLogView",
    "show_audit_log_view",
]
