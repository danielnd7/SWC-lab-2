from flask import Flask, request
from redis import Redis, RedisError
import os
import socket # To get the container ID/Hostname
from datetime import datetime # For timestamp conversion


# -------------------------------------------------------------
# Connect to Redis
# -------------------------------------------------------------
REDIS_HOST = os.getenv('REDIS_HOST', "localhost")
print("REDIS_HOST: " + REDIS_HOST)

try :
    redis = Redis(host=REDIS_HOST, port=6379, db=0, socket_connect_timeout=2, socket_timeout=2, decode_responses=True)
    redis.ping()  # Test the connection
except Exception as e:
    print("Error connecting to Redis:", str(e))
    redis = None
# -------------------------------------------------------------


def convert_timestamp(timestamp):
    '''Convertir un timestamp de milisegundos a una cadena legible'''
    dt_object = datetime.fromtimestamp(timestamp / 1000.0)
    return dt_object.strftime('%Y-%m-%d %H:%M:%S')



app = Flask(__name__)

@app.route('/')
def hello():
    try:
        visits = redis.incr("counter")
    except Exception as e:
        visits = "<i>cannot connect to Redis, counter disabled</i>"

    html = "<h3>Hello {name}!</h3>" \
           "<b>Hostname:</b> {hostname}<br/>" \
           "<b>Visits:</b> {visits}"
    return html.format(name=os.getenv("NAME", "world"), hostname=socket.gethostname(), visits=visits)


@app.route('/nuevo')
def new_measurement():
    # Obtener el parámetro 'dato' de la URL (si falla retorna None)
    dato = request.args.get('dato', type=float)

    if dato is None:
        return "Error: El parametro 'dato' es obligatorio y tiene que ser un float", 400
    
    else:
        try:
            # Añadir el valor a la serie temporal con la hora actual (el * indica añadir marca automáticamente)
            redis.execute_command('TS.ADD', 'temperature', '*', dato)
        except RedisError as e:
            return f"Error al insertar el dato en Redis: {str(e)}", 500
        except Exception as e:
            return f"Error desconocido al insertar el dato en Redis: {str(e)}", 500

        return f"Temperatura recibida: <b>{dato}°C</b> <br>Se ha agregado al Redis correctamente!", 200
    

@app.route('/listar')
def show_measurements():
    data_arr = [] # Lista para almacenar las cadenas formateadas

    hostname = socket.gethostname()
    title = f"<h2>Hostname : {hostname}</h2>"

    data_arr.append(title)

    try:
        # Obtener todos los datos de la serie temporal 'temperature'
        data = redis.execute_command('TS.RANGE', 'temperature', '-', '+')

        for sample in data:
            formated_timestamp = convert_timestamp(sample[0])
            data_arr.append(f"<b>{formated_timestamp} -----> {sample[1]} °C </b>")
        return '<br>'.join(data_arr), 200
    
    except RedisError as e:
        return f"Error al obtener los datos de Redis: {str(e)}", 500
    except Exception as e:
        return f"Error desconocido al obtener los datos de Redis: {str(e)}", 500


if __name__ == "__main__":
    PORT = os.getenv('PORT', 80)
    print("PORT: " + str(PORT))

    app.run(host='0.0.0.0', port=PORT, debug=True)