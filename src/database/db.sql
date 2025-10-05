CREATE TABLE socios (
        id_socio INTEGER NOT NULL,
        numero_socio VARCHAR NOT NULL,
        nombre VARCHAR NOT NULL,
        apellidos VARCHAR NOT NULL,
        telefono VARCHAR,
        email VARCHAR,
        forma_pago VARCHAR,
        fecha_alta DATE,
        estado VARCHAR,
        observaciones VARCHAR,
        PRIMARY KEY (id_socio),
        FOREIGN KEY(forma_pago) REFERENCES metodos_pago (id_metodo)
)

CREATE TABLE metodos_pago (
        id_metodo INTEGER NOT NULL,
        nombre VARCHAR NOT NULL,
        PRIMARY KEY (id_metodo),
        UNIQUE (nombre)
)

CREATE TABLE periodo (
        id_periodo INTEGER NOT NULL,
        nombre VARCHAR NOT NULL,
        fecha_inicio DATE NOT NULL,
        fecha_fin DATE NOT NULL,
        estado VARCHAR,
        PRIMARY KEY (id_periodo)
)

CREATE TABLE reglas_cobro (
        id_regla INTEGER NOT NULL,
        descripcion VARCHAR,
        cuota_mensual NUMERIC(10, 2),
        plazo_pago INTEGER,
        penalizacion NUMERIC(10, 2),
        descuento NUMERIC(10, 2),
        PRIMARY KEY (id_regla)
)

CREATE TABLE transacciones (
        id_transaccion INTEGER NOT NULL,
        numero_socio VARCHAR,
        id_periodo INTEGER,
        id_metodo INTEGER,
        tipo VARCHAR NOT NULL,
        monto NUMERIC(10, 2) NOT NULL,
        fecha DATE,
        estado VARCHAR,
        referencia VARCHAR,
        PRIMARY KEY (id_transaccion),
        FOREIGN KEY(numero_socio) REFERENCES socios (numero_socio),
        FOREIGN KEY(id_periodo) REFERENCES periodo (id_periodo),
        FOREIGN KEY(id_metodo) REFERENCES metodos_pago (id_metodo)
)

CREATE TABLE saldos_socios (
        id_saldo INTEGER NOT NULL,
        numero_socio VARCHAR,
        id_periodo INTEGER,
        saldo_anterior NUMERIC(10, 2),
        cargos NUMERIC(10, 2),
        pagos NUMERIC(10, 2),
        saldo_actual NUMERIC(10, 2),
        PRIMARY KEY (id_saldo),
        FOREIGN KEY(numero_socio) REFERENCES socios (numero_socio),
        FOREIGN KEY(id_periodo) REFERENCES periodo (id_periodo)
)

CREATE TABLE logs (
        id_log INTEGER NOT NULL,
        id_socio INTEGER,
        accion VARCHAR NOT NULL,
        tabla_afectada VARCHAR,
        id_registro_afectado INTEGER,
        descripcion_cambio VARCHAR,
        fecha_hora DATETIME,
        PRIMARY KEY (id_log),
        FOREIGN KEY(id_socio) REFERENCES socios (id_socio)
)
