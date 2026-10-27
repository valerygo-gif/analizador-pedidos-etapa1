from collections import defaultdict, deque
from copy import deepcopy
from html import escape

import math
import re


# =========================================================
# LECTURA DE LA EXPRESIÓN REGULAR
# =========================================================

class RegexParser:

    def __init__(self, expresion):
        # Guardamos la expresión y la posición que estamos leyendo.
        self.expresion = expresion
        self.posicion = 0


    def actual(self):
        # Devuelve el carácter actual de la expresión.
        if self.posicion < len(self.expresion):
            return self.expresion[self.posicion]

        return None


    def consumir(self, esperado=None):
        caracter = self.actual()

        if caracter is None:
            raise ValueError(
                "La expresión terminó antes de lo esperado."
            )

        if esperado is not None and caracter != esperado:
            raise ValueError(
                f"Se esperaba '{esperado}'."
            )

        self.posicion += 1

        return caracter


    def parsear(self):
        # Comenzamos interpretando toda la expresión.
        nodo = self._union()

        if self.posicion != len(self.expresion):
            raise ValueError(
                "No se pudo interpretar toda la expresión regular."
            )

        return nodo


    def _union(self):
        # El símbolo | indica que existen varias alternativas.
        opciones = [
            self._concatenacion()
        ]

        while self.actual() == "|":

            self.consumir("|")

            opciones.append(
                self._concatenacion()
            )

        if len(opciones) == 1:
            return opciones[0]

        return (
            "union",
            opciones
        )


    def _concatenacion(self):
        # Cuando varios elementos aparecen seguidos,
        # deben reconocerse en el mismo orden.
        partes = []

        while (
            self.actual() is not None
            and self.actual() not in ")|"
        ):

            partes.append(
                self._factor()
            )

        if not partes:
            return ("epsilon",)

        if len(partes) == 1:
            return partes[0]

        return (
            "concat",
            partes
        )


    def _factor(self):
        nodo = self._base()

        while True:

            # El asterisco permite cero o más repeticiones.
            if self.actual() == "*":

                self.consumir("*")

                nodo = (
                    "star",
                    nodo
                )

            # Una expresión como {3} indica exactamente
            # tres repeticiones del elemento anterior.
            elif self.actual() == "{":

                self.consumir("{")

                cantidad = ""

                while (
                    self.actual() is not None
                    and self.actual().isdigit()
                ):

                    cantidad += self.consumir()

                self.consumir("}")

                if not cantidad:
                    raise ValueError(
                        "La repetición necesita una cantidad."
                    )

                numero = int(cantidad)

                copias = [
                    deepcopy(nodo)
                    for _ in range(numero)
                ]

                if numero == 0:

                    nodo = ("epsilon",)

                elif numero == 1:

                    nodo = copias[0]

                else:

                    nodo = (
                        "concat",
                        copias
                    )

            else:

                break

        return nodo


    def _base(self):
        caracter = self.actual()

        # Los paréntesis permiten agrupar expresiones.
        if caracter == "(":

            self.consumir("(")

            nodo = self._union()

            self.consumir(")")

            return nodo


        # Aquí procesamos clases como [0-9] y [1-9].
        if caracter == "[":

            return self._clase()


        if caracter is None:

            raise ValueError(
                "Falta una parte de la expresión."
            )


        if caracter in "|)*{}":

            raise ValueError(
                f"Símbolo inesperado: {caracter}"
            )


        # Si no es un operador, se trata como un carácter normal.
        return (
            "literal",
            self.consumir()
        )


    def _clase(self):
        self.consumir("[")

        contenido = ""

        while (
            self.actual() is not None
            and self.actual() != "]"
        ):

            contenido += self.consumir()

        self.consumir("]")


        caracteres = set()

        indice = 0


        # Convertimos internamente, por ejemplo, 0-9
        # en los diez dígitos posibles.
        while indice < len(contenido):

            if (
                indice + 2 < len(contenido)
                and contenido[indice + 1] == "-"
            ):

                inicio = contenido[indice]
                fin = contenido[indice + 2]

                caracteres.update(
                    chr(valor)
                    for valor in range(
                        ord(inicio),
                        ord(fin) + 1
                    )
                )

                indice += 3

            else:

                caracteres.add(
                    contenido[indice]
                )

                indice += 1


        return (
            "clase",
            f"[{contenido}]",
            frozenset(caracteres)
        )


# =========================================================
# CONSTRUCCIÓN DEL AFND
# =========================================================

class ConstructorAFND:

    def __init__(self):
        self.contador = 0
        self.estados = set()
        self.transiciones = []


    def nuevo_estado(self):
        # Los estados se nombran q0, q1, q2...
        estado = f"q{self.contador}"

        self.contador += 1

        self.estados.add(
            estado
        )

        return estado


    def agregar_transicion(
        self,
        origen,
        simbolo,
        destino,
        caracteres=None
    ):

        self.transiciones.append({
            "origen": origen,
            "simbolo": simbolo,
            "destino": destino,
            "caracteres": caracteres
        })


    def construir(self, nodo):

        tipo = nodo[0]


        # Para un carácter normal creamos un estado
        # de entrada y otro de salida.
        if tipo == "literal":

            inicio = self.nuevo_estado()
            fin = self.nuevo_estado()

            self.agregar_transicion(
                inicio,
                nodo[1],
                fin,
                frozenset({
                    nodo[1]
                })
            )

            return inicio, fin


        # Las clases como [0-9] se conservan visualmente
        # como una sola transición.
        if tipo == "clase":

            inicio = self.nuevo_estado()
            fin = self.nuevo_estado()

            self.agregar_transicion(
                inicio,
                nodo[1],
                fin,
                nodo[2]
            )

            return inicio, fin


        # Epsilon permite pasar de estado sin consumir
        # ningún carácter de la entrada.
        if tipo == "epsilon":

            inicio = self.nuevo_estado()
            fin = self.nuevo_estado()

            self.agregar_transicion(
                inicio,
                "ε",
                fin
            )

            return inicio, fin


        # En una concatenación cada fragmento continúa
        # después del fragmento anterior.
        if tipo == "concat":

            inicio_general = None
            fin_anterior = None


            for parte in nodo[1]:

                inicio_parte, fin_parte = (
                    self.construir(
                        parte
                    )
                )


                if inicio_general is None:

                    inicio_general = (
                        inicio_parte
                    )

                else:

                    self.agregar_transicion(
                        fin_anterior,
                        "ε",
                        inicio_parte
                    )


                fin_anterior = fin_parte


            return (
                inicio_general,
                fin_anterior
            )


        # En una unión existen varios caminos posibles.
        if tipo == "union":

            inicio = self.nuevo_estado()
            fin = self.nuevo_estado()


            for opcion in nodo[1]:

                inicio_opcion, fin_opcion = (
                    self.construir(
                        opcion
                    )
                )


                self.agregar_transicion(
                    inicio,
                    "ε",
                    inicio_opcion
                )


                self.agregar_transicion(
                    fin_opcion,
                    "ε",
                    fin
                )


            return inicio, fin


        # El cierre permite repetir cero o más veces
        # la parte que se encuentra dentro.
        if tipo == "star":

            inicio = self.nuevo_estado()
            fin = self.nuevo_estado()

            inicio_interno, fin_interno = (
                self.construir(
                    nodo[1]
                )
            )


            self.agregar_transicion(
                inicio,
                "ε",
                fin
            )


            self.agregar_transicion(
                inicio,
                "ε",
                inicio_interno
            )


            self.agregar_transicion(
                fin_interno,
                "ε",
                inicio_interno
            )


            self.agregar_transicion(
                fin_interno,
                "ε",
                fin
            )


            return inicio, fin


        raise ValueError(
            "No se pudo construir una parte del AFND."
        )


# =========================================================
# FUNCIONES DE APOYO
# =========================================================

def numero_estado(estado):
    coincidencia = re.search(
        r"(\d+)$",
        estado
    )

    if coincidencia:

        return int(
            coincidencia.group(1)
        )

    return 99999


def ordenar_estados(estados):

    return sorted(
        estados,
        key=numero_estado
    )


# =========================================================
# EXPRESIÓN REGULAR -> AFND
# =========================================================

def construir_afnd(
    token,
    expresion
):

    # Primero interpretamos la expresión regular.
    parser = RegexParser(
        expresion
    )

    estructura = parser.parsear()


    # Después obtenemos los estados y las transiciones.
    constructor = ConstructorAFND()

    inicial, final = (
        constructor.construir(
            estructura
        )
    )


    # Epsilon no forma parte del alfabeto.
    alfabeto = sorted(
        set().union(
            *(
                transicion["caracteres"]
                or set()

                for transicion
                in constructor.transiciones
            )
        )
    )


    return {
        "tipo": "AFND",
        "token": token,
        "expresion": expresion,
        "estados":
            ordenar_estados(
                constructor.estados
            ),
        "alfabeto":
            alfabeto,
        "transiciones":
            constructor.transiciones,
        "inicial":
            inicial,
        "finales":
            {final}
    }


# =========================================================
# CIERRE EPSILON
# =========================================================

def cierre_epsilon(
    afnd,
    estados
):

    # Comenzamos con los mismos estados recibidos.
    cierre = set(
        estados
    )

    pendientes = list(
        estados
    )

    conexiones = defaultdict(
        list
    )


    # Guardamos únicamente las conexiones epsilon.
    for transicion in afnd["transiciones"]:

        if transicion["simbolo"] == "ε":

            conexiones[
                transicion["origen"]
            ].append(
                transicion["destino"]
            )


    # Seguimos las conexiones epsilon hasta que
    # ya no aparezca ningún estado nuevo.
    while pendientes:

        estado = pendientes.pop()


        for destino in conexiones[estado]:

            if destino not in cierre:

                cierre.add(
                    destino
                )

                pendientes.append(
                    destino
                )


    return frozenset(
        cierre
    )


def mover(
    afnd,
    estados,
    caracter
):

    # Busca todos los estados alcanzables consumiendo
    # exactamente el carácter recibido.
    destinos = set()


    for transicion in afnd["transiciones"]:

        if (
            transicion["origen"] in estados
            and
            transicion["caracteres"] is not None
            and
            caracter in transicion["caracteres"]
        ):

            destinos.add(
                transicion["destino"]
            )


    return destinos


# =========================================================
# AFND -> AFD
# =========================================================

def convertir_afnd_a_afd(afnd):

    # El primer estado del AFD representa el cierre
    # epsilon del estado inicial del AFND.
    conjunto_inicial = cierre_epsilon(
        afnd,
        {afnd["inicial"]}
    )


    nombres = {
        conjunto_inicial: "q0"
    }


    pendientes = deque([
        conjunto_inicial
    ])


    contador = 1

    transiciones = []


    while pendientes:

        conjunto_actual = (
            pendientes.popleft()
        )

        nombre_actual = (
            nombres[
                conjunto_actual
            ]
        )


        for simbolo in afnd["alfabeto"]:

            alcanzados = mover(
                afnd,
                conjunto_actual,
                simbolo
            )


            # Si no existe una transición para ese símbolo,
            # simplemente no agregamos ninguna.
            if not alcanzados:
                continue


            conjunto_destino = (
                cierre_epsilon(
                    afnd,
                    alcanzados
                )
            )


            if conjunto_destino not in nombres:

                nombres[
                    conjunto_destino
                ] = f"q{contador}"

                contador += 1

                pendientes.append(
                    conjunto_destino
                )


            transiciones.append({
                "origen":
                    nombre_actual,

                "simbolo":
                    simbolo,

                "destino":
                    nombres[
                        conjunto_destino
                    ]
            })


    finales_afnd = set(
        afnd["finales"]
    )

    finales_afd = set()


    # Un estado del AFD es final cuando su conjunto
    # contiene al estado final del AFND.
    for conjunto, nombre in nombres.items():

        if set(conjunto) & finales_afnd:

            finales_afd.add(
                nombre
            )


    subconjuntos = {}


    for conjunto, nombre in nombres.items():

        subconjuntos[
            nombre
        ] = ordenar_estados(
            conjunto
        )


    estados = sorted(
        nombres.values(),
        key=numero_estado
    )


    return {
        "tipo": "AFD",
        "token":
            afnd["token"],
        "expresion":
            afnd["expresion"],
        "estados":
            estados,
        "alfabeto":
            afnd["alfabeto"],
        "transiciones":
            transiciones,
        "inicial":
            "q0",
        "finales":
            finales_afd,
        "subconjuntos":
            subconjuntos
    }


# =========================================================
# SIMPLIFICAR SÍMBOLOS PARA MOSTRARLOS
# =========================================================

def compactar_caracteres(caracteres):

    pendientes = set(
        caracteres
    )

    partes = []


    digitos = set(
        "0123456789"
    )

    digitos_1_9 = set(
        "123456789"
    )


    # Cuando están presentes todos los dígitos,
    # los mostramos simplemente como [0-9].
    if digitos.issubset(
        pendientes
    ):

        partes.append(
            "[0-9]"
        )

        pendientes -= digitos


    # Si solamente están del 1 al 9,
    # utilizamos la notación [1-9].
    elif digitos_1_9.issubset(
        pendientes
    ):

        partes.append(
            "[1-9]"
        )

        pendientes -= digitos_1_9


    partes.extend(
        sorted(
            pendientes
        )
    )


    return ", ".join(
        partes
    )


# =========================================================
# AGRUPAR TRANSICIONES DEL AFD
# =========================================================

def agrupar_transiciones_afd(afd):

    grupos = defaultdict(
        set
    )


    # Si varios caracteres producen exactamente
    # la misma transición, los mostramos juntos.
    for transicion in afd["transiciones"]:

        clave = (
            transicion["origen"],
            transicion["destino"]
        )


        grupos[
            clave
        ].add(
            transicion["simbolo"]
        )


    resultado = []


    for (
        origen,
        destino
    ), caracteres in grupos.items():


        resultado.append({
            "origen":
                origen,

            "simbolo":
                compactar_caracteres(
                    caracteres
                ),

            "destino":
                destino
        })


    resultado.sort(
        key=lambda transicion: (
            numero_estado(
                transicion["origen"]
            ),
            numero_estado(
                transicion["destino"]
            ),
            transicion["simbolo"]
        )
    )


    return resultado


# =========================================================
# COLUMNAS Y TABLA DEL AFD
# =========================================================

def preparar_columnas_afd(afd):

    indice = {
        (
            transicion["origen"],
            transicion["simbolo"]
        ):
        transicion["destino"]

        for transicion
        in afd["transiciones"]
    }


    grupos = defaultdict(
        set
    )


    # Agrupamos símbolos que tienen exactamente
    # el mismo comportamiento en todos los estados.
    for simbolo in afd["alfabeto"]:

        comportamiento = tuple(

            indice.get(
                (
                    estado,
                    simbolo
                ),
                "—"
            )

            for estado
            in afd["estados"]
        )


        grupos[
            comportamiento
        ].add(
            simbolo
        )


    columnas = []


    for comportamiento, simbolos in grupos.items():

        columnas.append({
            "etiqueta":
                compactar_caracteres(
                    simbolos
                ),

            "comportamiento":
                comportamiento
        })


    columnas.sort(
        key=lambda columna:
            columna["etiqueta"]
    )


    return columnas


def preparar_tabla_afd(afd):

    columnas = preparar_columnas_afd(
        afd
    )

    filas = []


    for indice_estado, estado in enumerate(
        afd["estados"]
    ):

        celdas = []


        for columna in columnas:

            celdas.append(
                columna[
                    "comportamiento"
                ][indice_estado]
            )


        filas.append({
            "estado":
                estado,

            "es_inicial":
                estado == afd["inicial"],

            "es_final":
                estado in afd["finales"],

            "celdas":
                celdas
        })


    return columnas, filas


# =========================================================
# QUÍNTUPLA DEL AFD
# =========================================================

def preparar_quintupla(afd):

    # La representación formal es M = (Q, Σ, δ, q0, F).

    estados = (
        "{"
        + ", ".join(
            afd["estados"]
        )
        + "}"
    )


    alfabeto = (
        "{"
        + compactar_caracteres(
            afd["alfabeto"]
        )
        + "}"
    )


    transiciones = (
        agrupar_transiciones_afd(
            afd
        )
    )


    delta = []


    for transicion in transiciones:

        delta.append(
            "δ("
            + transicion["origen"]
            + ", "
            + transicion["simbolo"]
            + ") = "
            + transicion["destino"]
        )


    finales = (
        "{"
        + ", ".join(
            sorted(
                afd["finales"],
                key=numero_estado
            )
        )
        + "}"
    )


    return {
        "Q":
            estados,

        "Sigma":
            alfabeto,

        "delta":
            "{"
            + "; ".join(
                delta
            )
            + "}",

        "q0":
            afd["inicial"],

        "F":
            finales
    }


# =========================================================
# POSICIONES DE LOS ESTADOS PARA EL GRÁFICO
# =========================================================

def calcular_posiciones(automata):

    # Organizamos los estados por niveles para que
    # las ramas también puedan verse con claridad.
    adyacencia = defaultdict(
        list
    )


    if automata["tipo"] == "AFD":

        transiciones = (
            agrupar_transiciones_afd(
                automata
            )
        )

    else:

        transiciones = (
            automata["transiciones"]
        )


    for transicion in transiciones:

        if (
            transicion["origen"]
            != transicion["destino"]
        ):

            adyacencia[
                transicion["origen"]
            ].append(
                transicion["destino"]
            )


    niveles = {
        automata["inicial"]: 0
    }


    pendientes = deque([
        automata["inicial"]
    ])


    while pendientes:

        actual = (
            pendientes.popleft()
        )


        for destino in adyacencia[actual]:

            if destino not in niveles:

                niveles[destino] = (
                    niveles[actual] + 1
                )

                pendientes.append(
                    destino
                )


    ultimo_nivel = max(
        niveles.values(),
        default=0
    )


    for estado in automata["estados"]:

        if estado not in niveles:

            ultimo_nivel += 1

            niveles[
                estado
            ] = ultimo_nivel


    # En los AFND dejamos el único estado final
    # a la derecha de todas las ramas.
    if (
        automata["tipo"] == "AFND"
        and
        len(automata["finales"]) == 1
    ):

        final = next(
            iter(
                automata["finales"]
            )
        )


        if final != automata["inicial"]:

            maximo = max(
                (
                    nivel

                    for estado, nivel
                    in niveles.items()

                    if estado != final
                ),
                default=0
            )


            niveles[
                final
            ] = maximo + 1


    por_nivel = defaultdict(
        list
    )


    for estado in automata["estados"]:

        por_nivel[
            niveles[estado]
        ].append(
            estado
        )


    for grupo in por_nivel.values():

        grupo.sort(
            key=numero_estado
        )


    max_vertical = max(
        (
            len(grupo)
            for grupo
            in por_nivel.values()
        ),
        default=1
    )


    alto = max(
        340,
        150 + max_vertical * 105
    )


    max_nivel = max(
        por_nivel.keys(),
        default=0
    )


    ancho = max(
        850,
        220 + max_nivel * 145
    )


    posiciones = {}


    for nivel, grupo in por_nivel.items():

        separacion = 95

        altura_grupo = (
            len(grupo) - 1
        ) * separacion


        inicio_y = (
            alto / 2
            - altura_grupo / 2
        )


        for indice, estado in enumerate(
            grupo
        ):

            posiciones[
                estado
            ] = (
                90 + nivel * 145,
                inicio_y
                + indice * separacion
            )


    return (
        posiciones,
        ancho,
        alto
    )


# =========================================================
# GRÁFICO SVG GENERADO DESDE EL CÓDIGO
# =========================================================

def generar_svg(
    automata,
    identificador
):

    posiciones, ancho, alto = (
        calcular_posiciones(
            automata
        )
    )


    marcador = re.sub(
        r"[^A-Za-z0-9_]",
        "_",
        identificador
    )


    radio = 27

    partes = []


    partes.append(
        f'<svg '
        f'viewBox="0 0 {ancho} {alto}" '
        f'style="min-width:{ancho}px" '
        f'class="grafico-automata" '
        f'xmlns="http://www.w3.org/2000/svg">'
    )


    partes.append(
        f'<defs>'
        f'<marker '
        f'id="flecha_{marcador}" '
        f'markerWidth="10" '
        f'markerHeight="10" '
        f'refX="9" '
        f'refY="3" '
        f'orient="auto">'
        f'<path '
        f'd="M0,0 L0,6 L9,3 z" '
        f'fill="#24356f">'
        f'</path>'
        f'</marker>'
        f'</defs>'
    )


    if automata["tipo"] == "AFD":

        transiciones = (
            agrupar_transiciones_afd(
                automata
            )
        )

    else:

        transiciones = [
            {
                "origen":
                    transicion["origen"],

                "simbolo":
                    transicion["simbolo"],

                "destino":
                    transicion["destino"]
            }

            for transicion
            in automata["transiciones"]
        ]


    # Primero dibujamos las transiciones.
    for transicion in transiciones:

        origen = (
            transicion["origen"]
        )

        destino = (
            transicion["destino"]
        )

        simbolo = escape(
            transicion["simbolo"]
        )


        x1, y1 = posiciones[
            origen
        ]

        x2, y2 = posiciones[
            destino
        ]


        # Cuando una transición vuelve al mismo estado
        # utilizamos un pequeño arco.
        if origen == destino:

            partes.append(
                f'<path '
                f'd="M {x1 - 18} {y1 - 22} '
                f'C {x1 - 52} {y1 - 85}, '
                f'{x1 + 52} {y1 - 85}, '
                f'{x1 + 18} {y1 - 22}" '
                f'fill="none" '
                f'stroke="#24356f" '
                f'stroke-width="2" '
                f'marker-end="url(#flecha_{marcador})">'
                f'</path>'
            )


            partes.append(
                f'<text '
                f'x="{x1}" '
                f'y="{y1 - 72}" '
                f'text-anchor="middle" '
                f'font-size="13">'
                f'{simbolo}'
                f'</text>'
            )


            continue


        dx = x2 - x1
        dy = y2 - y1

        distancia = math.hypot(
            dx,
            dy
        )


        if distancia == 0:
            distancia = 1


        inicio_x = (
            x1
            + dx / distancia * radio
        )

        inicio_y = (
            y1
            + dy / distancia * radio
        )

        fin_x = (
            x2
            - dx / distancia
            * (radio + 7)
        )

        fin_y = (
            y2
            - dy / distancia
            * (radio + 7)
        )


        # Cuando la flecha regresa hacia un estado anterior
        # usamos una curva para que no se confunda con las demás.
        if x2 <= x1:

            control_x = (
                inicio_x + fin_x
            ) / 2

            control_y = min(
                inicio_y,
                fin_y
            ) - 75


            partes.append(
                f'<path '
                f'd="M {inicio_x} {inicio_y} '
                f'Q {control_x} {control_y} '
                f'{fin_x} {fin_y}" '
                f'fill="none" '
                f'stroke="#24356f" '
                f'stroke-width="2" '
                f'marker-end="url(#flecha_{marcador})">'
                f'</path>'
            )


            texto_x = control_x
            texto_y = control_y - 5

        else:

            partes.append(
                f'<line '
                f'x1="{inicio_x}" '
                f'y1="{inicio_y}" '
                f'x2="{fin_x}" '
                f'y2="{fin_y}" '
                f'stroke="#24356f" '
                f'stroke-width="2" '
                f'marker-end="url(#flecha_{marcador})">'
                f'</line>'
            )


            texto_x = (
                inicio_x + fin_x
            ) / 2

            texto_y = (
                inicio_y + fin_y
            ) / 2 - 8


        partes.append(
            f'<text '
            f'x="{texto_x}" '
            f'y="{texto_y}" '
            f'text-anchor="middle" '
            f'font-size="13">'
            f'{simbolo}'
            f'</text>'
        )


    # Flecha que señala el estado inicial.
    inicial = (
        automata["inicial"]
    )

    x_inicial, y_inicial = (
        posiciones[inicial]
    )


    partes.append(
        f'<line '
        f'x1="{x_inicial - 65}" '
        f'y1="{y_inicial}" '
        f'x2="{x_inicial - 35}" '
        f'y2="{y_inicial}" '
        f'stroke="#24356f" '
        f'stroke-width="2" '
        f'marker-end="url(#flecha_{marcador})">'
        f'</line>'
    )


    # Finalmente dibujamos los estados.
    for estado in automata["estados"]:

        x, y = posiciones[
            estado
        ]


        partes.append(
            f'<circle '
            f'cx="{x}" '
            f'cy="{y}" '
            f'r="{radio}" '
            f'fill="white" '
            f'stroke="#24356f" '
            f'stroke-width="2">'
            f'</circle>'
        )


        # Un estado final lleva doble círculo.
        if estado in automata["finales"]:

            partes.append(
                f'<circle '
                f'cx="{x}" '
                f'cy="{y}" '
                f'r="{radio - 6}" '
                f'fill="none" '
                f'stroke="#24356f" '
                f'stroke-width="2">'
                f'</circle>'
            )


        partes.append(
            f'<text '
            f'x="{x}" '
            f'y="{y + 5}" '
            f'text-anchor="middle" '
            f'font-size="13" '
            f'font-weight="bold">'
            f'{escape(estado)}'
            f'</text>'
        )


    partes.append(
        "</svg>"
    )


    return "".join(
        partes
    )