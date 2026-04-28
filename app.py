import os
import requests
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


# --- NUEVA FUNCIÓN PARA ENVIAR CORREOS VÍA API HTTP DE BREVO ---
def enviar_correo_alerta(asunto, mensaje, destino):
    # Obtenemos la API Key desde las variables de entorno
    def enviar_correo_alerta(asunto, mensaje, destino):
    api_key = os.getenv("BREVO_API_KEY")
    
    # Agrega esto temporalmente
    print(f"[DEBUG] API Key presente: {bool(api_key)}, longitud: {len(api_key) if api_key else 0}")
    
    if not api_key:
        raise ValueError("Falta BREVO_API_KEY en las variables de entorno")

    email_user = os.getenv("EMAIL_USER", "saimoljimenez@gmail.com")
    from_name = os.getenv("SMTP_FROM_NAME", "MediSync - Alertas")

    if not api_key:
        raise ValueError("Falta BREVO_API_KEY en las variables de entorno")

    url = "https://api.brevo.com/v3/smtp/email"
    
    # Cabeceras de la petición HTTP
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json"
    }
    
    # Cuerpo de la petición (Payload) en formato JSON
    payload = {
        "sender": {
            "name": from_name,
            "email": email_user
        },
        "to": [
            {
                "email": destino
            }
        ],
        "subject": asunto,
        "textContent": mensaje
    }

    try:
        # Hacemos la petición POST a Brevo con un timeout de 10 segundos
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        # Brevo devuelve 201 si el correo fue aceptado y puesto en cola correctamente
        if response.status_code not in [200, 201, 202]:
            raise RuntimeError(f"Error de Brevo API: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        # Capturamos cualquier error de red HTTP (no SMTP)
        raise RuntimeError(f"Error de red al conectar con Brevo: {e}")
# ---------------------------------------------------------------


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
        "BREVO_API_KEY_EXISTS": os.getenv("BREVO_API_KEY"),
        "EMAIL_USER": os.getenv("EMAIL_USER", "saimoljimenez@gmail.com")
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
            "message": "Correo enviado correctamente vía Brevo"
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