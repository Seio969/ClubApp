"""Settings feature: a hub screen (Ajustes) plus one package per section.

metodos_pago and reglas_cobro each get their own view/toolbar/dialog/
service set, following the same per-section file naming.
"""

from .menu_view import SettingsView, show_settings_view
from .metodos_pago_view import MetodosPagoView, show_metodos_pago_view
from .metodos_pago_toolbar import MetodosPagoToolBar
from .reglas_cobro_view import ReglasCobroView, show_reglas_cobro_view
from .reglas_cobro_toolbar import ReglasCobroToolBar

__all__ = [
    "SettingsView",
    "show_settings_view",
    "MetodosPagoView",
    "show_metodos_pago_view",
    "MetodosPagoToolBar",
    "ReglasCobroView",
    "show_reglas_cobro_view",
    "ReglasCobroToolBar",
]
