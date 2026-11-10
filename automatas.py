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

    # El estado inicial se reserva ANTES de generar el núcleo.
    # Así cada AFND independiente comienza siempre en q0.
    inicio = constructor.nuevo_estado()
    nucleo_inicio, nucleo_fin = constructor.construir(arbol)
    fin = constructor.nuevo_estado()
    constructor.agregar_transicion(inicio, EPSILON, nucleo_inicio)
    constructor.agregar_transicion(nucleo_fin, EPSILON, fin)

    estados = [f"q{i}" for i in range(constructor.contador)]
    alfabeto = sorted({
        t["simbolo"]
        for t in constructor.transiciones
        if t["simbolo"] != EPSILON
    })

    afnd = {
        "tipo": "AFND",
        "token": token,
        "expresion": expresion,
        "estados": estados,
        "alfabeto": alfabeto,
        "transiciones": constructor.transiciones,
        "inicial": inicio,
        "finales": [fin],
    }
    # Para la exposición: numeración consecutiva en el orden visual
    # (izquierda a derecha y, por nivel, de arriba abajo).
    niveles = calcular_niveles(afnd)
    orden = sorted(estados, key=lambda e: (niveles[e], int(e[1:])))
    nombres = {e: f"q{i}" for i, e in enumerate(orden)}
    afnd["estados"] = [nombres[e] for e in orden]
    afnd["inicial"] = nombres[inicio]
    afnd["finales"] = [nombres[fin]]
    afnd["transiciones"] = [
        {"origen": nombres[t["origen"]], "simbolo": t["simbolo"],
         "destino": nombres[t["destino"]]}
        for t in constructor.transiciones
    ]
    return afnd


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


def resumir_simbolos(simbolos):
    """Muestra cada símbolo explícitamente, sin abreviar intervalos (0–9, a–z)."""
    simbolos = set(simbolos)
    ordenados = []
    if EPSILON in simbolos:
        ordenados.append(EPSILON)
        simbolos.remove(EPSILON)
    ordenados.extend(sorted(simbolos))
    return ", ".join(ordenados)


def generar_svg(automata, identificador):
    """SVG íntegro: estado q0 a la izquierda, finales dobles, flechas y etiquetas visibles.

    Todas las etiquetas muestran los símbolos uno por uno (por ejemplo,
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9), distribuidos en líneas cuando corresponde.
    """
    import re

    def formato(valor):
        return f"{valor:.1f}"

    niveles = calcular_niveles(automata)
    por_nivel = defaultdict(list)
    for estado in automata["estados"]:
        por_nivel[niveles[estado]].append(estado)
    for estados in por_nivel.values():
        estados.sort(key=lambda e: int(e[1:]) if e[1:].isdigit() else e)

    transiciones = defaultdict(set)
    for t in automata["transiciones"]:
        transiciones[(t["origen"], t["destino"])].add(t["simbolo"])

    max_nivel = max(por_nivel, default=0)
    max_por_nivel = max(map(len, por_nivel.values()), default=1)
    # Separa automáticamente los estados según el ancho de sus etiquetas.
    # Se muestran como máximo diez símbolos por línea, sin abreviar rangos.
    max_caracteres = max(
        (
            len(", ".join(sorted(simbolos)[i:i + 10]))
            for simbolos in transiciones.values()
            for i in range(0, len(simbolos), 10)
        ),
        default=0,
    )
    paso_x = max(176, int(max_caracteres * 7.25 + 100))
    paso_y = 152
    margen_x = 115
    margen_y = 110
    ancho = margen_x * 2 + max_nivel * paso_x
    alto = max(290, 2 * margen_y + (max_por_nivel - 1) * paso_y)
    posiciones = {}
    centro_y = alto / 2
    for nivel in range(max_nivel + 1):
        estados = por_nivel.get(nivel, [])
        primer_y = centro_y - (len(estados) - 1) * paso_y / 2
        for i, estado in enumerate(estados):
            posiciones[estado] = (margen_x + nivel * paso_x, primer_y + i * paso_y)

    identificador = re.sub(r"[^A-Za-z0-9_-]", "_", identificador)
    marker = f"flecha_{identificador}"
    partes = [
        f'<svg class="grafico-automata" xmlns="http://www.w3.org/2000/svg" '
        f'data-ancho="{ancho}" width="{ancho}" height="{alto}" viewBox="0 0 {ancho} {alto}" '
        f'role="img" aria-label="{escape(automata["tipo"])} del token {escape(automata["token"])}">',
        '<defs>',
        f'<marker id="{marker}" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">',
        '<path d="M0,0 L9,3 L0,6 Z" fill="#344054" />',
        '</marker></defs>',
    ]
    # Entrada siempre visible y orientada desde la izquierda.
    xi, yi = posiciones[automata["inicial"]]
    partes.append(f'<path d="M {xi-80} {yi} L {xi-32} {yi}" stroke="#344054" '
                  f'stroke-width="2" fill="none" marker-end="url(#{marker})"/>')
    partes.append(f'<text x="{xi-75}" y="{yi-11}" font-size="12" fill="#475467">Inicio</text>')

    # Todas las transiciones se agrupan por PAR de estados, pero preservan todos los símbolos.
    for idx, ((origen, destino), simbolos) in enumerate(transiciones.items()):
        x1, y1 = posiciones[origen]
        x2, y2 = posiciones[destino]
        etiqueta = resumir_simbolos(simbolos)
        texto = escape(etiqueta)
        completo = escape(", ".join(sorted(simbolos)))
        if origen == destino:
            # Bucle con etiqueta encima; se deja margen para que no se recorte.
            x, y = x1, y1
            partes.append(f'<g><title>{completo}</title><path '
                          f'd="M {x-18} {y-25} C {x-55} {y-89}, {x+55} {y-89}, {x+18} {y-25}" '
                          f'fill="none" stroke="#344054" stroke-width="2" '
                          f'marker-end="url(#{marker})" />')
            tx, ty = x, y-87
        else:
            dx, dy = x2-x1, y2-y1
            distancia = max(math.hypot(dx,dy), 1)
            ux, uy = dx/distancia, dy/distancia
            sx, sy = x1+ux*29, y1+uy*29
            ex, ey = x2-ux*35, y2-uy*35
            # Desviación para flechas inversas o dos caminos entre iguales niveles.
            reversa = (destino, origen) in transiciones
            if x2 > x1 and not reversa:
                camino = f"M {formato(sx)} {formato(sy)} L {formato(ex)} {formato(ey)}"
                tx, ty = (sx+ex)/2, (sy+ey)/2-12
            else:
                # Si hay dos flechas en sentidos opuestos, separarlas por
                # lados distintos evita ocultar símbolos y etiquetas.
                desplazamiento = -100 if (x2 > x1 and reversa) else 100
                controlx=(sx+ex)/2
                controly=(sy+ey)/2+desplazamiento
                camino=(f"M {formato(sx)} {formato(sy)} Q "
                        f"{formato(controlx)} {formato(controly)} {formato(ex)} {formato(ey)}")
                tx, ty = (sx+2*controlx+ex)/4, (sy+2*controly+ey)/4-12
            partes.append(f'<g><title>{completo}</title><path d="{camino}" fill="none" '
                          f'stroke="#344054" stroke-width="2" marker-end="url(#{marker})"/>')
        # Rectángulo blanco dimensionado según el texto, para impedir superposiciones.
        # Cortes solo entre símbolos: nunca parten una etiqueta por la mitad.
        elementos = etiqueta.split(", ")
        lineas = [", ".join(elementos[i:i + 10])
                  for i in range(0, len(elementos), 10)] or [""]
        maxlen = max(map(len,lineas))
        caja_ancho = max(30, maxlen*7.25+15)
        caja_alto = len(lineas)*16+8
        partes.append(f'<rect x="{formato(tx-caja_ancho/2)}" y="{formato(ty-caja_alto+8)}" '
                      f'width="{formato(caja_ancho)}" height="{caja_alto}" rx="4" '
                      f'fill="white" stroke="#d0d5dd" stroke-width="0.5"/>')
        for lin, linea in enumerate(lineas):
            partes.append(f'<text x="{formato(tx)}" y="{formato(ty-(len(lineas)-1-lin)*16)}" '
                          f'text-anchor="middle" font-size="12" fill="#101828">{escape(linea)}</text>')
        partes.append('</g>')

    # Estados se dibujan AL FINAL para que las flechas no atraviesen los círculos.
    for estado in automata["estados"]:
        x,y=posiciones[estado]
        partes.append(f'<circle cx="{x}" cy="{formato(y)}" r="28" '
                      'fill="#fff" stroke="#4f46e5" stroke-width="2.2"/>')
        if estado in automata["finales"]:
            partes.append(f'<circle cx="{x}" cy="{formato(y)}" r="22.5" '
                          'fill="none" stroke="#4f46e5" stroke-width="2"/>')
        partes.append(f'<text x="{x}" y="{formato(y+5)}" text-anchor="middle" '
                      f'font-size="13" font-weight="700" fill="#111827">{escape(estado)}</text>')
    partes.append('</svg>')
    return "".join(partes)


def exportar_jflap(automata):
    """Exporta el AFND o AFD a formato .jff para contrastarlo en JFLAP.

    Conserva las transiciones sin agrupar; las epsilon usan <read />.
    """
    import xml.etree.ElementTree as ET
    raiz = ET.Element("structure")
    ET.SubElement(raiz, "type").text = "fa"
    cuerpo = ET.SubElement(raiz, "automaton")
    niveles = calcular_niveles(automata)
    por_nivel = defaultdict(list)
    for estado in automata["estados"]:
        por_nivel[niveles[estado]].append(estado)
    for nivel, estados in sorted(por_nivel.items()):
        for fila, nombre in enumerate(estados):
            nodo = ET.SubElement(cuerpo, "state", {
                "id": nombre[1:], "name": nombre,
            })
            ET.SubElement(nodo, "x").text = str(110 + nivel * 155)
            ET.SubElement(nodo, "y").text = str(120 + fila * 115)
            if nombre == automata["inicial"]:
                ET.SubElement(nodo, "initial")
            if nombre in automata["finales"]:
                ET.SubElement(nodo, "final")
    for t in automata["transiciones"]:
        trans = ET.SubElement(cuerpo, "transition")
        ET.SubElement(trans, "from").text = t["origen"][1:]
        ET.SubElement(trans, "to").text = t["destino"][1:]
        ET.SubElement(trans, "read").text = (
            None if t["simbolo"] == EPSILON else t["simbolo"]
        )
    ET.indent(raiz, space="  ")
    return ET.tostring(raiz, encoding="utf-8", xml_declaration=True)