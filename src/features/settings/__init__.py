"""Settings feature: a hub screen (Ajustes) plus one package per section.

Currently: metodos_pago (view/toolbar/dialog/service). Billing rules
(reglas_cobro) will follow the same per-section file naming.
"""

from .menu_view import SettingsView, show_settings_view
from .metodos_pago_view import MetodosPagoView, show_metodos_pago_view
from .metodos_pago_toolbar import MetodosPagoToolBar

__all__ = [
    "SettingsView",
    "show_settings_view",
    "MetodosPagoView",
    "show_metodos_pago_view",
    "MetodosPagoToolBar",
]
