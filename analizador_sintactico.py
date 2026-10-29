SECUENCIA_ESPERADA = [
    "KW_REGLA",
    "ID_REGLA",
    "KW_SI",
    "CAMPO",
    "OPERADOR",
    "NUMERO",
    "KW_ENTONCES",
    "ACCION",
    "DESTINO",
    "FIN",
]


def analizar_sintaxis(resultados):
    # Si existe un lexema desconocido no podemos continuar
    # con el análisis sintáctico.
    for resultado in resultados:
        if resultado["token"] == "DESCONOCIDO":
            return {
                "valida": False,
                "mensaje":
                    "No se puede validar la sintaxis porque "
                    "existe al menos un error léxico.",
                "representacion": None,
            }

    tokens = [
        resultado["token"]
        for resultado in resultados
    ]

    # Comparamos la secuencia encontrada con la estructura
    # definida para nuestro mini lenguaje.
    if tokens != SECUENCIA_ESPERADA:

        limite = min(
            len(tokens),
            len(SECUENCIA_ESPERADA)
        )

        for indice in range(limite):

            if tokens[indice] != SECUENCIA_ESPERADA[indice]:

                posicion = indice + 1

                return {
                    "valida": False,
                    "mensaje": (
                        f"Error sintáctico en la posición "
                        f"{posicion}: se esperaba "
                        f"{SECUENCIA_ESPERADA[indice]} "
                        f"y se encontró {tokens[indice]}."
                    ),
                    "representacion": None,
                }

        if len(tokens) < len(SECUENCIA_ESPERADA):

            return {
                "valida": False,
                "mensaje": (
                    "La regla está incompleta. "
                    f"Falta al menos el token "
                    f"{SECUENCIA_ESPERADA[len(tokens)]}."
                ),
                "representacion": None,
            }

        return {
            "valida": False,
            "mensaje":
                "La regla contiene elementos adicionales "
                "que no forman parte de la gramática definida.",
            "representacion": None,
        }

    lexemas = [
        resultado["lexema"]
        for resultado in resultados
    ]

    # Después de validar la regla organizamos su información.
    # Esta es una representación intermedia, todavía no es
    # la traducción final de un compilador completo.
    representacion = {
        "id_regla": lexemas[1],

        "condicion": {
            "campo": lexemas[3],
            "operador": lexemas[4],
            "valor": lexemas[5],
        },

        "accion": {
            "tipo": lexemas[7],
            "destino": lexemas[8],
        },
    }

    return {
        "valida": True,
        "mensaje":
            "Sintaxis correcta: la regla cumple "
            "la estructura definida por el mini lenguaje.",
        "representacion": representacion,
    }