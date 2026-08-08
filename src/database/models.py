from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Numeric, UniqueConstraint, Boolean
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()

class Socio(Base):
    __tablename__ = "socios"
    id_socio = Column(Integer, primary_key=True, index=True)
    # numero_socio is a family/shared number; not unique across rows
    numero_socio = Column(String, nullable=False)
    nombre = Column(String, nullable=False)
    apellidos = Column(String, nullable=False)
    telefono = Column(String)
    email = Column(String)
    fecha_alta = Column(Date)
    estado = Column(String, default="activo")
    observaciones = Column(String)
    # primary holder per numero_socio - exactly one True per shared family
    # number, enforced in MembersService.add_member/update_member, never at
    # the DB layer (see PLAN.md 2.17).
    es_titular = Column(Boolean, nullable=False, default=False)

    # relationships: use class names and matching back_populates attribute names
    transacciones = relationship("Transaccion", back_populates="socio")
    saldos = relationship("SaldoSocios", back_populates="socio")
    logs = relationship("Log", back_populates="socio")


class MetodoPago(Base):
    __tablename__ = "metodos_pago"
    id_metodo = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, unique=True)
    # activo/inactivo, same soft-deactivation pattern as Socio.estado - a
    # payment method is never physically deleted, only deactivated, so
    # transactions that already reference it keep a meaningful name.
    estado = Column(String, default="activo")

    transacciones = relationship("Transaccion", back_populates="metodo")


class Periodo(Base):
    __tablename__ = "periodo"
    id_periodo = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    estado = Column(String, default="abierto")

    transacciones = relationship("Transaccion", back_populates="periodo")
    saldos = relationship("SaldoSocios", back_populates="periodo")


class ReglaCobro(Base):
    __tablename__ = "reglas_cobro"
    id_regla = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String)
    cuota_mensual = Column(Numeric(10, 2))
    plazo_pago = Column(Integer)
    penalizacion = Column(Numeric(10, 2))
    descuento = Column(Numeric(10, 2))
    # activo/inactivo - same soft-deactivation pattern as Socio.estado and
    # MetodoPago.estado; a rule is never physically deleted so a
    # transaction/period that already referenced it keeps a meaningful name.
    estado = Column(String, default="activo")


class Transaccion(Base):
    __tablename__ = "transacciones"
    id_transaccion = Column(Integer, primary_key=True, index=True)
    # transactions are linked to the family member number (numero_socio)
    numero_socio = Column(String, ForeignKey("socios.numero_socio"))
    id_periodo = Column(Integer, ForeignKey("periodo.id_periodo"))
    id_metodo = Column(Integer, ForeignKey("metodos_pago.id_metodo"))
    tipo = Column(String, nullable=False)  # cargo/pago/reembolso
    monto = Column(Numeric(10, 2), nullable=False)
    fecha = Column(Date, default=datetime.date.today)
    referencia = Column(String)

    # relationship to Socio (singular) and back_populates must match attribute name on Socio
    socio = relationship("Socio", back_populates="transacciones")
    periodo = relationship("Periodo", back_populates="transacciones")
    metodo = relationship("MetodoPago", back_populates="transacciones")


class SaldoSocios(Base):
    __tablename__ = "saldos_socios"
    __table_args__ = (UniqueConstraint('numero_socio', 'id_periodo', name='uq_saldos_numero_periodo'),)
    id_saldo = Column(Integer, primary_key=True, index=True)
    numero_socio = Column(String, ForeignKey("socios.numero_socio"))
    id_periodo = Column(Integer, ForeignKey("periodo.id_periodo"))
    saldo_anterior = Column(Numeric(10, 2), default=0)
    cargos = Column(Numeric(10, 2), default=0)
    pagos = Column(Numeric(10, 2), default=0)
    saldo_actual = Column(Numeric(10, 2), default=0)


    # singular relationship name for the related Socio
    socio = relationship("Socio", back_populates="saldos")
    periodo = relationship("Periodo", back_populates="saldos")


class Log(Base):
    __tablename__ = "logs"
    id_log = Column(Integer, primary_key=True, index=True)
    id_socio = Column(Integer, ForeignKey("socios.id_socio"))
    accion = Column(String, nullable=False)
    tabla_afectada = Column(String)
    id_registro_afectado = Column(Integer)
    descripcion_cambio = Column(String)
    fecha_hora = Column(DateTime, default=datetime.datetime.now)

    # singular relationship to Socio
    socio = relationship("Socio", back_populates="logs")
