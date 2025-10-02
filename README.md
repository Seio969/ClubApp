## Lenguage y Framework
 - Python 
 - PySide6
 - SQLite


# Requisitos Funcionales

## Gestión de Usuarios
- Registrar, editar y desactivar socios: Permite crear nuevos socios, modificar sus datos personales y desactivarlos sin eliminar su historial.
- Almacenar datos de miembros: Guarda información como nombre completo, datos de contacto (teléfono, email), fecha de alta, estado (activo/inactivo), y observaciones adicionales.

## Transacciones Financieras
- Registrar cargos, pagos y reembolsos: Permite ingresar cuotas, pagos realizados por los socios y devoluciones de dinero.
- Soportar múltiples métodos de pago: Admite efectivo, transferencia bancaria, Bizum, y otros métodos configurables.
- Arrastrar saldos de meses anteriores: Calcula automáticamente los saldos pendientes o a favor de cada socio de un mes a otro.

### Formas de Pago:
- **REMESA:** Pago domiciliado mediante recibo bancario, gestionado automáticamente por el club.
- **EFECTIVO:** Pago realizado en mano, directamente al responsable del club.
- **TRANSFERENCIA:** Pago realizado mediante transferencia bancaria directa a la cuenta del club.
- **TRANSFERENCIA/EFECTIVO:** Combinación de ambos métodos; parte del pago se realiza por transferencia y el resto en efectivo.
- **INACTIVO:** Indica que el socio está dado de baja y no realiza pagos, o que el pago corresponde a una baja administrativa.

## Reportes
- Resúmenes anuales por socio: Genera informes detallados de movimientos y saldos de cada socio durante el año.
- Visión financiera anual completa: Muestra el balance global del club, ingresos, egresos y deudas acumuladas.
- Exportar reportes a Excel/PDF: Permite descargar los informes en formatos estándar para compartir o archivar.

## Configuración
- Definir reglas para cargos, plazos de pago, penalizaciones: Configura cuotas mensuales, fechas límite de pago, recargos por retraso y descuentos.
- Gestionar meses/períodos activos: Permite abrir, cerrar o modificar períodos contables y asociar transacciones a cada uno.

## Búsqueda y Filtros
- Búsqueda rápida por socio: Localiza socios por nombre, apellidos o número de socio.
- Filtrar transacciones por fecha, tipo o estado: Permite ver solo los movimientos de un periodo, tipo de operación (cargo/pago/reembolso) o estado (pendiente, pagado, reembolsado).

## Integridad de Datos
- Cálculo automático de saldos: El sistema actualiza los saldos de cada socio tras cada operación.
- Prevenir registros inconsistentes: Impide, por ejemplo, registrar un reembolso si no hay un pago previo o duplicar transacciones.

## Diagramas y Estadísticas
- Gráficas: Muestra la evolución de pagos, deudas y recaudación a lo largo del tiempo, así como la distribución de deudas entre socios.
- Panel de estadísticas: Incluye totales recaudados, promedios de pago, número de socios al día y saldos pendientes.

## Copia de Seguridad de la Base de Datos
- Copias automáticas programadas: Realiza backups diarios o semanales de la base de datos para evitar pérdida de información.
- Opción de copia y restauración manual: Permite al usuario descargar una copia de seguridad o restaurar el sistema desde un backup anterior.

## Registro de Actividad (Logging)
- Registrar cada cambio: Guarda cada acción, qué modificó y cuándo lo hizo.
- Historial de auditoría: Permite consultar todos los cambios realizados en los registros financieros y miembros


# Requisitos No Funcionales

- **Rendimiento:** Manejar hasta miles de socios y transacciones por año de manera eficiente.  
- **Escalabilidad:** Permitir migración de SQLite (local) → PostgreSQL (servidor).  
- **Seguridad:**  
  - Almacenamiento cifrado de datos sensibles.   
- **Usabilidad:**  
  - Interfaz sencilla, similar a flujos de trabajo en Excel.  
  - Importación *drag-and-drop* desde hojas de cálculo.  
- **Mantenibilidad:** Arquitectura limpia, código modular.  
- **Confiabilidad:** Operaciones financieras seguras en transacciones (ACID).  
