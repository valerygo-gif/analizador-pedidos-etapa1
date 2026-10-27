from flask import Flask, render_template, request

from analizador_lexico import identificar_token

from automatas import (
    construir_afnd,
    convertir_afnd_a_afd,
    preparar_tabla_afd,
    preparar_quintupla,
    agrupar_transiciones_afd,
    generar_svg
)


app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def inicio():

    # Aquí guardamos el resultado obtenido para cada lexema.
    resultados = []

    # Aquí guardamos los desarrollos formales
    # que se mostrarán debajo del análisis léxico.
    automatas = []

    texto = ""

    tiene_errores = False


    if request.method == "POST":

        # Recibimos lo escrito en la caja de texto.
        texto = request.form.get(
            "texto",
            ""
        ).strip()


        # También permitimos analizar un archivo TXT.
        archivo = request.files.get(
            "archivo"
        )


        if archivo and archivo.filename:

            texto = (
                archivo
                .read()
                .decode("utf-8")
                .strip()
            )


        if texto:

            # Por ahora cada elemento separado por espacios
            # se considera un lexema.
            elementos = texto.split()


            for posicion, lexema in enumerate(
                elementos,
                start=1
            ):

                token, expresion = (
                    identificar_token(
                        lexema
                    )
                )


                resultados.append({
                    "posicion":
                        posicion,

                    "lexema":
                        lexema,

                    "token":
                        token,

                    "expresion":
                        expresion
                })


            # Si aparece un lexema desconocido,
            # mostramos que hubo un error léxico.
            tiene_errores = any(
                resultado["token"]
                == "DESCONOCIDO"

                for resultado
                in resultados
            )


            reglas_generadas = set()


            for resultado in resultados:

                token = (
                    resultado["token"]
                )

                expresion = (
                    resultado["expresion"]
                )


                if token == "DESCONOCIDO":
                    continue


                # Evitamos repetir un desarrollo si una misma
                # regla aparece dos veces en la cadena.
                clave = (
                    token,
                    expresion
                )


                if clave in reglas_generadas:
                    continue


                # Construimos el AFND correspondiente
                # a la expresión regular.
                afnd = construir_afnd(
                    token,
                    expresion
                )


                # Obtenemos el AFD equivalente.
                afd = convertir_afnd_a_afd(
                    afnd
                )


                # Preparamos las columnas y filas
                # que aparecerán en la tabla del AFD.
                columnas, tabla = (
                    preparar_tabla_afd(
                        afd
                    )
                )


                afd["columnas"] = columnas

                afd["tabla"] = tabla


                # Agrupamos transiciones equivalentes
                # para mostrarlas de forma más sencilla.
                afd[
                    "transiciones_mostradas"
                ] = agrupar_transiciones_afd(
                    afd
                )


                # Construimos los cinco componentes formales
                # del AFD.
                afd["quintupla"] = (
                    preparar_quintupla(
                        afd
                    )
                )


                # Los gráficos se crean directamente
                # desde los estados y transiciones calculados.
                afnd["svg"] = generar_svg(
                    afnd,
                    f"afnd_{token}"
                )


                afd["svg"] = generar_svg(
                    afd,
                    f"afd_{token}"
                )


                automatas.append({
                    "token":
                        token,

                    "expresion":
                        expresion,

                    "ejemplo":
                        resultado["lexema"],

                    "afnd":
                        afnd,

                    "afd":
                        afd
                })


                reglas_generadas.add(
                    clave
                )


    return render_template(
        "index.html",
        resultados=resultados,
        automatas=automatas,
        texto=texto,
        tiene_errores=tiene_errores
    )


if __name__ == "__main__":

    app.run(debug=True)