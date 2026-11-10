# Gramática de la fase actual (los valores son tokens del análisis léxico):
# Programa -> Regla Programa | Regla
# Regla -> KW_REGLA ID_REGLA KW_SI CAMPO OPERADOR NUMERO
#          KW_ENTONCES ACCION DESTINO FIN
# Esta fase verifica estructura; NO interpreta ni ejecuta reglas comerciales.
SECUENCIA_ESPERADA = [
    "KW_REGLA", "ID_REGLA", "KW_SI", "CAMPO", "OPERADOR", "NUMERO",
    "KW_ENTONCES", "ACCION", "DESTINO", "FIN",
]


def analizar_sintaxis(resultados):
    for resultado in resultados:
        if resultado["token"] == "DESCONOCIDO":
            return {
                "valida": False,
                "mensaje": "No se puede validar la sintaxis: hay al menos un lexema no reconocido.",
                "representacion": None,
                "representaciones": [],
            }

    if not resultados:
        return {"valida": False, "mensaje": "Escribe al menos una regla.",
                "representacion": None, "representaciones": []}

    tokens = [r["token"] for r in resultados]
    representaciones = []
    longitud = len(SECUENCIA_ESPERADA)
    for comienzo in range(0, len(tokens), longitud):
        fragmento = tokens[comienzo:comienzo+longitud]
        for indice, esperado in enumerate(SECUENCIA_ESPERADA):
            if indice >= len(fragmento):
                return {
                    "valida": False,
                    "mensaje": (f"Regla {comienzo//longitud+1} incompleta: "
                                f"en la posición {comienzo+indice+1} falta {esperado}."),
                    "representacion": None, "representaciones": [],
                }
            if fragmento[indice] != esperado:
                return {
                    "valida": False,
                    "mensaje": (f"Error sintáctico en posición {comienzo+indice+1}: "
                                f"se esperaba {esperado}, se encontró {fragmento[indice]}."),
                    "representacion": None, "representaciones": [],
                }

        lexemas = [r["lexema"] for r in resultados[comienzo:comienzo+longitud]]
        representaciones.append({
            "id_regla": lexemas[1],
            "condicion": {"campo": lexemas[3], "operador": lexemas[4],
                          "valor": lexemas[5]},
            "accion": {"tipo": lexemas[7], "destino": lexemas[8]},
        })

    return {
        "valida": True,
        "mensaje": f"Sintaxis correcta: {len(representaciones)} regla(s) válidas.",
        "representacion": representaciones[0],
        "representaciones": representaciones,
    }