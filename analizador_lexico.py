import re


# Aquí definimos cada token junto con la expresión regular
# que permite reconocerlo dentro de una cadena de pedido.
REGLAS_LEXICAS = [
    ("PEDIDO", r"PEDIDO"),
    ("CLIENTE", r"CLIENTE"),
    ("PRODUCTO", r"PRODUCTO"),
    ("CANTIDAD", r"CANTIDAD"),
    ("PAGO", r"PAGO"),

    ("ID_PRODUCTO", r"PR[0-9]{3}"),
    ("ID_PEDIDO", r"P[0-9]{3}"),
    ("ID_CLIENTE", r"C[0-9]{3}"),

    ("NUMERO", r"[1-9][0-9]*"),

    ("METODO_PAGO", r"EFECTIVO|TARJETA|YAPE|PLIN"),

    ("FIN", r";"),
]


def identificar_token(lexema):
    # Recorremos las reglas hasta encontrar una expresión
    # que coincida completamente con el lexema recibido.
    for token, expresion in REGLAS_LEXICAS:

        if re.fullmatch(expresion, lexema):
            return token, expresion

    # Si ninguna regla coincide, el lexema no es reconocido.
    return "DESCONOCIDO", "No definida"