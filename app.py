from flask import Flask, render_template, request

app = Flask(__name__)


def identificar_token(elemento):
    if elemento in ["PEDIDO", "CLIENTE", "PRODUCTO", "CANTIDAD", "PAGO"]:
        return "PALABRA_CLAVE"

    if elemento.startswith("PR") and len(elemento) == 5 and elemento[2:].isdigit():
        return "ID_PRODUCTO"

    if elemento.startswith("P") and len(elemento) == 4 and elemento[1:].isdigit():
        return "ID_PEDIDO"

    if elemento.startswith("C") and len(elemento) == 4 and elemento[1:].isdigit():
        return "ID_CLIENTE"

    if elemento.isdigit():
        return "NUMERO"

    if elemento in ["EFECTIVO", "TARJETA", "YAPE", "PLIN"]:
        return "METODO_PAGO"

    if elemento == ";":
        return "FIN"

    return "DESCONOCIDO"


@app.route("/", methods=["GET", "POST"])
def inicio():
    resultados = []
    texto = ""

    if request.method == "POST":

        texto = request.form.get("texto", "").strip()

        archivo = request.files.get("archivo")

        if archivo and archivo.filename:
            texto = archivo.read().decode("utf-8").strip()

        if texto:
            elementos = texto.split()

            for elemento in elementos:
                resultados.append({
                    "token": identificar_token(elemento),
                    "lexema": elemento
                })

    return render_template(
        "index.html",
        resultados=resultados,
        texto=texto
    )


if __name__ == "__main__":
    app.run(debug=True)