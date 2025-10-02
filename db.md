```mermaid
erDiagram

    usuarios {
        int id_usuario
        string numero_socio
        string nombre
        string apellidos
        string telefono
        string email
        date fecha_alta
        string estado
        string observaciones
    }

    metodos_pago {
        int id_metodo
        string nombre
    }

    periodo {
        int id_periodo
        string nombre
        date fecha_inicio
        date fecha_fin
        string estado
    }

    reglas_cobro {
        int id_regla
        string descripcion
        float cuota_mensual
        int plazo_pago
        float penalizacion
        float descuento
    }

    transacciones {
        int id_transaccion
        int id_usuario
        int id_periodo
        int id_metodo
        string tipo
        float monto
        date fecha
        string estado
        string referencia
    }

    saldos_usuarios {
        int id_saldo
        int id_usuario
        int id_periodo
        float saldo_anterior
        float cargos
        float pagos
        float saldo_actual
    }

    logs {
        int id_log
        int id_usuario
        string accion
        string tabla_afectada
        int id_registro_afectado
        string descripcion_cambio
        date fecha_hora
    }

    %% Relationships
    usuarios ||--o{ transacciones : realiza
    periodo ||--o{ transacciones : pertenece
    metodos_pago ||--o{ transacciones : usa

    usuarios ||--o{ saldos_usuarios : tiene
    periodo ||--o{ saldos_usuarios : corresponde

    usuarios ||--o{ logs : genera
