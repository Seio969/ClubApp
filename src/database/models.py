from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import declarative_base, relationship
import datetime

Base = declarative_base()

class Usuario(Base):
    __tablename__ = "usuarios"
    id_usuario = Column(Integer, primary_key=True, index=True)
    numero_socio = Column(String, unique=True, nullable=False)
    nombre = Column(String, nullable=False)
    apellidos = Column(String, nullable=False)
    telefono = Column(String)
    email = Column(String)
    fecha_alta = Column(Date)
    estado = Column(String, default="activo")
    observaciones = Column(String)

    transacciones = relationship("Transaccion", back_populates="usuario")
    saldos = relationship("SaldoUsuario", back_populates="usuario")
    logs = relationship("Log", back_populates="usuario")


class MetodoPago(Base):
    __tablename__ = "metodos_pago"
    id_metodo = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False, unique=True)

    transacciones = relationship("Transaccion", back_populates="metodo")


class Periodo(Base):
    __tablename__ = "periodo"
    id_periodo = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    estado = Column(String, default="abierto")

    transacciones = relationship("Transaccion", back_populates="periodo")
    saldos = relationship("SaldoUsuario", back_populates="periodo")


class ReglaCobro(Base):
    __tablename__ = "reglas_cobro"
    id_regla = Column(Integer, primary_key=True, index=True)
    descripcion = Column(String)
    cuota_mensual = Column(Numeric(10, 2))
    plazo_pago = Column(Integer)
    penalizacion = Column(Numeric(10, 2))
    descuento = Column(Numeric(10, 2))


class Transaccion(Base):
    __tablename__ = "transacciones"
    id_transaccion = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"))
    id_periodo = Column(Integer, ForeignKey("periodo.id_periodo"))
    id_metodo = Column(Integer, ForeignKey("metodos_pago.id_metodo"))
    tipo = Column(String, nullable=False)  # cargo/pago/reembolso
    monto = Column(Numeric(10, 2), nullable=False)
    fecha = Column(Date, default=datetime.date.today)
    estado = Column(String, default="pendiente")
    referencia = Column(String)

    usuario = relationship("Usuario", back_populates="transacciones")
    periodo = relationship("Periodo", back_populates="transacciones")
    metodo = relationship("MetodoPago", back_populates="transacciones")


class SaldoUsuario(Base):
    __tablename__ = "saldos_usuarios"
    id_saldo = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"))
    id_periodo = Column(Integer, ForeignKey("periodo.id_periodo"))
    saldo_anterior = Column(Numeric(10, 2), default=0)
    cargos = Column(Numeric(10, 2), default=0)
    pagos = Column(Numeric(10, 2), default=0)
    saldo_actual = Column(Numeric(10, 2), default=0)

    usuario = relationship("Usuario", back_populates="saldos")
    periodo = relationship("Periodo", back_populates="saldos")


class Log(Base):
    __tablename__ = "logs"
    id_log = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"))
    accion = Column(String, nullable=False)
    tabla_afectada = Column(String)
    id_registro_afectado = Column(Integer)
    descripcion_cambio = Column(String)
    fecha_hora = Column(DateTime, default=datetime.datetime.now)

    usuario = relationship("Usuario", back_populates="logs")
