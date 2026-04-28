import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import Flask, jsonify, request
from flask_cors import CORS  # Importante para que WordPress pueda hacer la petición
from mssql_python import connect

app = Flask(__name__)

# Habilitar CORS para permitir peticiones desde tu frontend de WordPress
CORS(app)


def get_connection():
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_DATABASE")
    username = os.getenv("DB_USERNAME")
    password = os.getenv("DB_PASSWORD")
    port = os.getenv("DB_PORT", "1433")

    if not server:
        raise ValueError("Falta DB_SERVER")
    if not database:
        raise ValueError("Falta DB_DATABASE")
    if not username:
        raise ValueError("Falta DB_USERNAME")
    if not password:
        raise ValueError("Falta DB_PASSWORD")

    connection_string = (
        f"Server=tcp:{server},{port};"
        f"Database={database};"
        f"Uid={username};"
        f"Pwd={password};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=no;"
        f"Authentication=SqlPassword;"
    )

    return connect(connection_string)


# --- NUEVA FUNCIÓN PARA ENVIAR CORREOS ---
def enviar_correo_alerta(asunto, mensaje, destino):
    # Usamos variables de entorno para proteger las credenciales
    smtp_user = os.getenv("SMTP_USER")      # ej: saimoljimenez@gmail.com
    smtp_pass = os.getenv("SMTP_PASSWORD")  # ej: tu nueva contraseña de aplicación
    from_name = os.getenv("SMTP_FROM_NAME", "Alertas")
    
    if not smtp_user or not smtp_pass:
        raise ValueError("Faltan las credenciales SMTP en las variables de entorno")

    # Configuración del mensaje
    msg = MIMEMultipart()
    msg['From'] = f"{from_name} <{smtp_user}>"
    msg['To'] = destino
    msg['Subject'] = asunto

    # Adjuntar el cuerpo del mensaje
    msg.attach(MIMEText(mensaje, 'plain'))

    # Conexión al servidor SMTP de Gmail
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()  # Activar encriptación SSL/TLS
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        raise Exception(f"Error en el servidor SMTP: {str(e)}")
# -----------------------------------------


@app.route("/")
def home():
    return jsonify({
        "success": True,
        "message": "API Flask funcionando correctamente en Render"
    })


@app.route("/debug-env")
def debug_env():
    return jsonify({
        "DB_SERVER": os.getenv("DB_SERVER"),
        "DB_DATABASE": os.getenv("DB_DATABASE"),
        "DB_USERNAME": os.getenv("DB_USERNAME"),
        "DB_PASSWORD_EXISTS": bool(os.getenv("DB_PASSWORD")),
        "DB_PORT": os.getenv("DB_PORT"),
        "SMTP_USER_EXISTS": bool(os.getenv("SMTP_USER")),
        "SMTP_PASSWORD_EXISTS": bool(os.getenv("SMTP_PASSWORD"))
    })


@app.route("/test-db")
def test_db():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT GETDATE() AS fecha_servidor")
        row = cursor.fetchone()

        return jsonify({
            "success": True,
            "message": "Conexión a SQL Server exitosa",
            "server_date": str(row[0])
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error al conectar con SQL Server",
            "error": str(e)
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route("/enviar-alerta", methods=["POST"])
def enviar_alerta():
    try:
        # request.get_json() ahora funcionará porque importamos 'request'
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "message": "No se recibió un JSON válido"}), 400

        destino = data.get("to")
        asunto = data.get("subject")
        mensaje = data.get("message")

        if not destino or not asunto or not mensaje:
            return jsonify({
                "success": False,
                "message": "Faltan datos (to, subject o message)"
            }), 400

        # Llamamos a la función que acabamos de definir
        enviar_correo_alerta(asunto, mensaje, destino)

        return jsonify({
            "success": True,
            "message": "Correo enviado correctamente"
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/productos")
def listar_productos():
    conn = None
    cursor = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT TOP 20 Id, Nombre, Precio, UrlImagen, Stock
            FROM Productos
            ORDER BY Id DESC
        """)
        rows = cursor.fetchall()

        data = []
        for row in rows:
            data.append({
                "id": row[0],
                "nombre": row[1],
                "precio": float(row[2]) if row[2] is not None else None,
                "imagen_url": row[3],
                "stock": row[4],
            })

        return jsonify({
            "success": True,
            "data": data
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Error al consultar productos",
            "error": str(e)
        }), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)