import re

# Cada regla asocia un tipo de token con la expresión regular
# que reconoce ese elemento dentro del mini lenguaje.
REGLAS_LEXICAS = [
    ("KW_REGLA", r"REGLA"),
    ("KW_SI", r"SI"),
    ("KW_ENTONCES", r"ENTONCES"),

    ("CAMPO", r"TOTAL|CANTIDAD"),
    ("ACCION", r"AUTORIZAR|VALIDAR"),
    ("DESTINO", r"SUPERVISOR|STOCK"),

    ("ID_REGLA", r"R[0-9]{3}"),
    ("OPERADOR", r">=|<=|>|<|="),
    ("NUMERO", r"[1-9][0-9]*"),

    ("FIN", r";"),
]


def tokenizar_cadena(texto):
    # Separamos palabras, números, operadores y el punto y coma.
    # Así no es obligatorio colocar espacios alrededor de cada símbolo.
    patron = re.compile(
        r">=|<=|>|<|=|;|[A-Za-z_][A-Za-z_0-9]*|[0-9]+|\S"
    )

    return patron.findall(texto)


def identificar_token(lexema):
    # Probamos el lexema contra cada regla hasta encontrar
    # una coincidencia completa.
    for token, expresion in REGLAS_LEXICAS:
        if re.fullmatch(expresion, lexema):
            return token, expresion

    return "DESCONOCIDO", "No definida"