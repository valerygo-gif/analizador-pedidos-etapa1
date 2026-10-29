from collections import defaultdict, deque
from html import escape
import math

EPSILON = "ε"


class RegexParser:
    def __init__(self, expresion):
        self.expresion = expresion
        self.posicion = 0

    def actual(self):
        if self.posicion >= len(self.expresion):
            return None
        return self.expresion[self.posicion]

    def consumir(self, esperado=None):
        caracter = self.actual()
        if caracter is None:
            return None
        if esperado is not None and caracter != esperado:
            raise ValueError(f"Se esperaba '{esperado}' y se encontró '{caracter}'.")
        self.posicion += 1
        return caracter

    def parsear(self):
        nodo = self.parsear_union()
        if self.actual() is not None:
            raise ValueError("La expresión regular contiene elementos que no pudieron interpretarse.")
        return nodo

    def parsear_union(self):
        nodos = [self.parsear_concatenacion()]

        while self.actual() == "|":
            self.consumir("|")
            nodos.append(self.parsear_concatenacion())

        if len(nodos) == 1:
            return nodos[0]
        return ("union", nodos)

    def parsear_concatenacion(self):
        nodos = []

        while self.actual() is not None and self.actual() not in ")|":
            nodos.append(self.parsear_repeticion())

        if not nodos:
            return ("epsilon",)
        if len(nodos) == 1:
            return nodos[0]
        return ("concat", nodos)

    def parsear_repeticion(self):
        nodo = self.parsear_atomo()

        while True:
            if self.actual() == "*":
                self.consumir("*")
                nodo = ("estrella", nodo)
            elif self.actual() == "+":
                self.consumir("+")
                nodo = ("mas", nodo)
            elif self.actual() == "?":
                self.consumir("?")
                nodo = ("opcional", nodo)
            elif self.actual() == "{":
                self.consumir("{")
                numeros = []
                while self.actual() is not None and self.actual().isdigit():
                    numeros.append(self.consumir())
                self.consumir("}")
                if not numeros:
                    raise ValueError("La repetición exacta necesita un número.")
                nodo = ("repetir", nodo, int("".join(numeros)))
            else:
                break

        return nodo

    def parsear_atomo(self):
        caracter = self.actual()

        if caracter is None:
            return ("epsilon",)

        if caracter == "(":
            self.consumir("(")
            nodo = self.parsear_union()
            self.consumir(")")
            return nodo

        if caracter == "[":
            return self.parsear_clase()

        if caracter == "\\":
            self.consumir("\\")
            literal = self.consumir()
            return ("literal", literal)

        self.consumir()
        return ("literal", caracter)

    def parsear_clase(self):
        self.consumir("[")
        contenido = []

        while self.actual() is not None and self.actual() != "]":
            contenido.append(self.consumir())

        self.consumir("]")
        texto = "".join(contenido)
        caracteres = []
        indice = 0

        while indice < len(texto):
            if indice + 2 < len(texto) and texto[indice + 1] == "-":
                inicio = ord(texto[indice])
                fin = ord(texto[indice + 2])
                paso = 1 if inicio <= fin else -1
                caracteres.extend(chr(codigo) for codigo in range(inicio, fin + paso, paso))
                indice += 3
            else:
                caracteres.append(texto[indice])
                indice += 1

        return ("clase", tuple(dict.fromkeys(caracteres)))


class ConstructorAFND:
    def __init__(self):
        self.contador = 0
        self.transiciones = []

    def nuevo_estado(self):
        estado = f"q{self.contador}"
        self.contador += 1
        return estado

    def agregar_transicion(self, origen, simbolo, destino):
        self.transiciones.append({
            "origen": origen,
            "simbolo": simbolo,
            "destino": destino,
        })

    def construir(self, nodo):
        tipo = nodo[0]

        if tipo == "epsilon":
            inicio = self.nuevo_estado()
            fin = self.nuevo_estado()
            self.agregar_transicion(inicio, EPSILON, fin)
            return inicio, fin

        if tipo == "literal":
            inicio = self.nuevo_estado()
            fin = self.nuevo_estado()
            self.agregar_transicion(inicio, nodo[1], fin)
            return inicio, fin

        if tipo == "clase":
            inicio = self.nuevo_estado()
            fin = self.nuevo_estado()
            for caracter in nodo[1]:
                self.agregar_transicion(inicio, caracter, fin)
            return inicio, fin

        if tipo == "concat":
            primero_inicio = None
            anterior_fin = None

            for subnodo in nodo[1]:
                inicio, fin = self.construir(subnodo)
                if primero_inicio is None:
                    primero_inicio = inicio
                if anterior_fin is not None:
                    self.agregar_transicion(anterior_fin, EPSILON, inicio)
                anterior_fin = fin

            return primero_inicio, anterior_fin

        if tipo == "union":
            inicio = self.nuevo_estado()
            fin = self.nuevo_estado()

            for subnodo in nodo[1]:
                sub_inicio, sub_fin = self.construir(subnodo)
                self.agregar_transicion(inicio, EPSILON, sub_inicio)
                self.agregar_transicion(sub_fin, EPSILON, fin)

            return inicio, fin

        if tipo == "estrella":
            inicio = self.nuevo_estado()
            fin = self.nuevo_estado()
            sub_inicio, sub_fin = self.construir(nodo[1])

            self.agregar_transicion(inicio, EPSILON, fin)
            self.agregar_transicion(inicio, EPSILON, sub_inicio)
            self.agregar_transicion(sub_fin, EPSILON, sub_inicio)
            self.agregar_transicion(sub_fin, EPSILON, fin)
            return inicio, fin

        if tipo == "mas":
            inicio = self.nuevo_estado()
            fin = self.nuevo_estado()
            sub_inicio, sub_fin = self.construir(nodo[1])

            self.agregar_transicion(inicio, EPSILON, sub_inicio)
            self.agregar_transicion(sub_fin, EPSILON, sub_inicio)
            self.agregar_transicion(sub_fin, EPSILON, fin)
            return inicio, fin

        if tipo == "opcional":
            inicio = self.nuevo_estado()
            fin = self.nuevo_estado()
            sub_inicio, sub_fin = self.construir(nodo[1])

            self.agregar_transicion(inicio, EPSILON, fin)
            self.agregar_transicion(inicio, EPSILON, sub_inicio)
            self.agregar_transicion(sub_fin, EPSILON, fin)
            return inicio, fin

        if tipo == "repetir":
            cantidad = nodo[2]
            if cantidad == 0:
                return self.construir(("epsilon",))

            primero_inicio = None
            anterior_fin = None

            for _ in range(cantidad):
                inicio, fin = self.construir(nodo[1])
                if primero_inicio is None:
                    primero_inicio = inicio
                if anterior_fin is not None:
                    self.agregar_transicion(anterior_fin, EPSILON, inicio)
                anterior_fin = fin

            return primero_inicio, anterior_fin

        raise ValueError(f"Tipo de nodo no soportado: {tipo}")


def construir_afnd(token, expresion):
    parser = RegexParser(expresion)
    arbol = parser.parsear()
    constructor = ConstructorAFND()

    nucleo_inicio, nucleo_fin = constructor.construir(arbol)

    # Envolvemos el núcleo con transiciones epsilon para que la representación
    # del AFND sea explícitamente no determinista y luego pueda convertirse a AFD.
    inicio = constructor.nuevo_estado()
    fin = constructor.nuevo_estado()
    constructor.agregar_transicion(inicio, EPSILON, nucleo_inicio)
    constructor.agregar_transicion(nucleo_fin, EPSILON, fin)

    estados = [f"q{i}" for i in range(constructor.contador)]
    alfabeto = sorted({
        t["simbolo"]
        for t in constructor.transiciones
        if t["simbolo"] != EPSILON
    })

    return {
        "tipo": "AFND",
        "token": token,
        "expresion": expresion,
        "estados": estados,
        "alfabeto": alfabeto,
        "transiciones": constructor.transiciones,
        "inicial": inicio,
        "finales": [fin],
    }


def cierre_epsilon(estados, transiciones):
    cierre = set(estados)
    pila = list(estados)

    mapa = defaultdict(list)
    for transicion in transiciones:
        if transicion["simbolo"] == EPSILON:
            mapa[transicion["origen"]].append(transicion["destino"])

    while pila:
        estado = pila.pop()
        for destino in mapa[estado]:
            if destino not in cierre:
                cierre.add(destino)
                pila.append(destino)

    return frozenset(cierre)


def mover(estados, simbolo, transiciones):
    destinos = set()
    for transicion in transiciones:
        if transicion["origen"] in estados and transicion["simbolo"] == simbolo:
            destinos.add(transicion["destino"])
    return destinos


def convertir_afnd_a_afd(afnd):
    alfabeto = afnd["alfabeto"]
    inicio_conjunto = cierre_epsilon({afnd["inicial"]}, afnd["transiciones"])

    nombres = {inicio_conjunto: "q0"}
    pendientes = deque([inicio_conjunto])
    conjuntos_ordenados = [inicio_conjunto]
    transiciones_afd = []

    while pendientes:
        conjunto_actual = pendientes.popleft()
        origen = nombres[conjunto_actual]

        for simbolo in alfabeto:
            movidos = mover(conjunto_actual, simbolo, afnd["transiciones"])
            if not movidos:
                continue

            destino_conjunto = cierre_epsilon(movidos, afnd["transiciones"])
            if not destino_conjunto:
                continue

            if destino_conjunto not in nombres:
                nombre = f"q{len(nombres)}"
                nombres[destino_conjunto] = nombre
                pendientes.append(destino_conjunto)
                conjuntos_ordenados.append(destino_conjunto)

            transiciones_afd.append({
                "origen": origen,
                "simbolo": simbolo,
                "destino": nombres[destino_conjunto],
            })

    final_afnd = set(afnd["finales"])
    finales_afd = [
        nombres[conjunto]
        for conjunto in conjuntos_ordenados
        if set(conjunto) & final_afnd
    ]

    equivalencias = [
        {
            "afd": nombres[conjunto],
            "afnd": sorted(conjunto, key=lambda e: int(e[1:])),
        }
        for conjunto in conjuntos_ordenados
    ]

    return {
        "tipo": "AFD",
        "token": afnd["token"],
        "expresion": afnd["expresion"],
        "estados": [nombres[c] for c in conjuntos_ordenados],
        "alfabeto": alfabeto,
        "transiciones": transiciones_afd,
        "inicial": "q0",
        "finales": finales_afd,
        "equivalencias": equivalencias,
    }


def agrupar_transiciones(automata):
    agrupadas = defaultdict(list)

    for transicion in automata["transiciones"]:
        clave = (transicion["origen"], transicion["destino"])
        agrupadas[clave].append(transicion["simbolo"])

    resultado = []
    for (origen, destino), simbolos in agrupadas.items():
        epsilon = [s for s in simbolos if s == EPSILON]
        normales = sorted({s for s in simbolos if s != EPSILON})
        etiquetas = epsilon + normales
        resultado.append({
            "origen": origen,
            "simbolo": ", ".join(etiquetas),
            "destino": destino,
        })

    return resultado


def preparar_tabla_afd(afd):
    columnas = afd["alfabeto"]
    mapa = {
        (t["origen"], t["simbolo"]): t["destino"]
        for t in afd["transiciones"]
    }

    filas = []
    for estado in afd["estados"]:
        filas.append({
            "estado": estado,
            "inicial": estado == afd["inicial"],
            "final": estado in afd["finales"],
            "destinos": [mapa.get((estado, simbolo), "—") for simbolo in columnas],
        })

    return columnas, filas


def preparar_quintupla(afd):
    transiciones = [
        f"δ({t['origen']}, {t['simbolo']}) = {t['destino']}"
        for t in afd["transiciones"]
    ]

    return {
        "Q": "{" + ", ".join(afd["estados"]) + "}",
        "Sigma": "{" + ", ".join(afd["alfabeto"]) + "}",
        "delta": transiciones,
        "q0": afd["inicial"],
        "F": "{" + ", ".join(afd["finales"]) + "}",
    }


def calcular_niveles(automata):
    niveles = {automata["inicial"]: 0}
    cola = deque([automata["inicial"]])

    adyacencia = defaultdict(list)
    for transicion in automata["transiciones"]:
        if transicion["destino"] != transicion["origen"]:
            adyacencia[transicion["origen"]].append(transicion["destino"])

    while cola:
        origen = cola.popleft()
        for destino in adyacencia[origen]:
            nuevo_nivel = niveles[origen] + 1
            if destino not in niveles or nuevo_nivel < niveles[destino]:
                niveles[destino] = nuevo_nivel
                cola.append(destino)

    maximo = max(niveles.values(), default=0)
    for estado in automata["estados"]:
        if estado not in niveles:
            maximo += 1
            niveles[estado] = maximo

    return niveles


def generar_svg(automata, identificador):
    transiciones = agrupar_transiciones(automata)
    niveles = calcular_niveles(automata)

    por_nivel = defaultdict(list)
    for estado in automata["estados"]:
        por_nivel[niveles[estado]].append(estado)

    for estados in por_nivel.values():
        estados.sort(key=lambda e: int(e[1:]) if e[1:].isdigit() else e)

    max_nivel = max(por_nivel.keys(), default=0)
    max_por_nivel = max((len(v) for v in por_nivel.values()), default=1)

    ancho = max(760, 160 + max_nivel * 145)
    alto = max(260, 110 + max_por_nivel * 115)
    centro_y = alto / 2

    posiciones = {}
    for nivel in range(max_nivel + 1):
        estados = por_nivel.get(nivel, [])
        if not estados:
            continue

        separacion = 105
        bloque = (len(estados) - 1) * separacion
        inicio_y = centro_y - bloque / 2

        for indice, estado in enumerate(estados):
            posiciones[estado] = (90 + nivel * 145, inicio_y + indice * separacion)

    marker = f"flecha_{identificador}"
    partes = [
        f'<svg class="grafico-automata" viewBox="0 0 {ancho} {alto}" role="img" aria-label="{escape(automata["tipo"])} de {escape(automata["token"])}">',
        '<defs>',
        f'<marker id="{marker}" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth">',
        '<path d="M0,0 L0,6 L9,3 z" fill="#344054" />',
        '</marker>',
        '</defs>',
    ]

    # Flecha de inicio.
    x0, y0 = posiciones[automata["inicial"]]
    partes.append(
        f'<line x1="{x0 - 58}" y1="{y0}" x2="{x0 - 31}" y2="{y0}" '
        f'stroke="#344054" stroke-width="2" marker-end="url(#{marker})" />'
    )
    partes.append(
        f'<text x="{x0 - 62}" y="{y0 - 10}" text-anchor="middle" font-size="12" fill="#667085">Inicio</text>'
    )

    for indice, transicion in enumerate(transiciones):
        origen = transicion["origen"]
        destino = transicion["destino"]
        etiqueta = escape(transicion["simbolo"])
        x1, y1 = posiciones[origen]
        x2, y2 = posiciones[destino]

        if origen == destino:
            partes.append(
                f'<path d="M {x1 - 18} {y1 - 24} C {x1 - 55} {y1 - 72}, {x1 + 55} {y1 - 72}, {x1 + 18} {y1 - 24}" '
                f'fill="none" stroke="#344054" stroke-width="2" marker-end="url(#{marker})" />'
            )
            partes.append(
                f'<text x="{x1}" y="{y1 - 76}" text-anchor="middle" font-size="12" fill="#101828">{etiqueta}</text>'
            )
            continue

        radio = 25
        dx = x2 - x1
        dy = y2 - y1
        distancia = max(math.hypot(dx, dy), 1)
        ux, uy = dx / distancia, dy / distancia
        sx, sy = x1 + ux * radio, y1 + uy * radio
        ex, ey = x2 - ux * 31, y2 - uy * 31

        if x2 > x1:
            partes.append(
                f'<line x1="{sx}" y1="{sy}" x2="{ex}" y2="{ey}" '
                f'stroke="#344054" stroke-width="2" marker-end="url(#{marker})" />'
            )
            tx = (sx + ex) / 2
            ty = (sy + ey) / 2 - 8
        else:
            curvatura = 55 + (indice % 3) * 16
            cx1 = sx + 45
            cy1 = sy - curvatura
            cx2 = ex - 45
            cy2 = ey - curvatura
            partes.append(
                f'<path d="M {sx} {sy} C {cx1} {cy1}, {cx2} {cy2}, {ex} {ey}" '
                f'fill="none" stroke="#344054" stroke-width="2" marker-end="url(#{marker})" />'
            )
            tx = (sx + ex) / 2
            ty = min(cy1, cy2) - 5

        partes.append(
            f'<rect x="{tx - 34}" y="{ty - 13}" width="68" height="18" rx="4" fill="white" opacity="0.92" />'
        )
        partes.append(
            f'<text x="{tx}" y="{ty}" text-anchor="middle" font-size="11" fill="#101828">{etiqueta}</text>'
        )

    for estado in automata["estados"]:
        x, y = posiciones[estado]
        final = estado in automata["finales"]

        partes.append(
            f'<circle cx="{x}" cy="{y}" r="25" fill="#ffffff" stroke="#4f46e5" stroke-width="2" />'
        )
        if final:
            partes.append(
                f'<circle cx="{x}" cy="{y}" r="20" fill="none" stroke="#4f46e5" stroke-width="2" />'
            )

        partes.append(
            f'<text x="{x}" y="{y + 4}" text-anchor="middle" font-size="12" font-weight="700" fill="#111827">{escape(estado)}</text>'
        )

    partes.append('</svg>')
    return "".join(partes)
