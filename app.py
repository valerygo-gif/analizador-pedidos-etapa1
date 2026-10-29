from flask import Flask, render_template, request

from analizador_lexico import (
    identificar_token,
    tokenizar_cadena
)

from analizador_sintactico import analizar_sintaxis

from automatas import (
    construir_afnd,
    convertir_afnd_a_afd,
    preparar_tabla_afd,
    preparar_quintupla,
    agrupar_transiciones,
    generar_svg
)


app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def inicio():

    resultados = []
    automatas = []

    texto = ""

    tiene_errores_lexicos = False
    sintaxis = None

    if request.method == "POST":

        texto = request.form.get(
            "texto",
            ""
        ).strip()

        archivo = request.files.get(
            "archivo"
        )

        if archivo and archivo.filename:

            texto = archivo.read().decode(
                "utf-8"
            ).strip()

        if texto:

            lexemas = tokenizar_cadena(texto)

            for posicion, lexema in enumerate(
                lexemas,
                start=1
            ):

                token, expresion = identificar_token(
                    lexema
                )

                resultados.append({
                    "posicion": posicion,
                    "lexema": lexema,
                    "token": token,
                    "expresion": expresion
                })

            tiene_errores_lexicos = any(
                resultado["token"] == "DESCONOCIDO"
                for resultado in resultados
            )

            sintaxis = analizar_sintaxis(
                resultados
            )

            reglas_generadas = set()

            for resultado in resultados:

                token = resultado["token"]
                expresion = resultado["expresion"]

                if token == "DESCONOCIDO":
                    continue

                clave = (
                    token,
                    expresion
                )

                if clave in reglas_generadas:
                    continue

                afnd = construir_afnd(
                    token,
                    expresion
                )

                afd = convertir_afnd_a_afd(
                    afnd
                )

                columnas, tabla = preparar_tabla_afd(
                    afd
                )

                afd["columnas"] = columnas
                afd["tabla"] = tabla

                afd["transiciones_mostradas"] = (
                    agrupar_transiciones(afd)
                )

                afd["quintupla"] = (
                    preparar_quintupla(afd)
                )

                afnd["transiciones_mostradas"] = (
                    agrupar_transiciones(afnd)
                )

                afnd["svg"] = generar_svg(
                    afnd,
                    f"afnd_{token}"
                )

                afd["svg"] = generar_svg(
                    afd,
                    f"afd_{token}"
                )

                automatas.append({
                    "token": token,
                    "expresion": expresion,
                    "ejemplo": resultado["lexema"],
                    "afnd": afnd,
                    "afd": afd
                })

                reglas_generadas.add(
                    clave
                )

    return render_template(
        "index.html",
        resultados=resultados,
        automatas=automatas,
        texto=texto,
        tiene_errores_lexicos=tiene_errores_lexicos,
        sintaxis=sintaxis
    )


if __name__ == "__main__":
    app.run(debug=True)