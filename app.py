# ========================================================================
# BLOOMA - MERCADO MELCHOR OCAMPO
# ========================================================================
# app.py - ARCHIVO PRINCIPAL DE LA APLICACIÓN FLASK
#
# ESTE ARCHIVO CONTIENE TODA LA LÓGICA DEL BACKEND: RUTAS, AUTENTICACIÓN,
# CARRITO DE COMPRAS CON CONTROL DE STOCK EN TIEMPO REAL, GESTIÓN DE
# PEDIDOS, ADMINISTRACIÓN DE LOCALES, PRODUCTOS, USUARIOS, ETC.
#
# EL SISTEMA PERMITE QUE LOS CLIENTES AGREGUEN PRODUCTOS AL CARRITO Y
# EL STOCK SE DESCUENTE INMEDIATAMENTE, LIBERÁNDOSE SI EL CLIENTE
# REDUCE CANTIDADES O ELIMINA EL PRODUCTO. ASÍ SE EVITA LA SOBREVENTA.
#
# SE HA AÑADIDO UN MÓDULO COMPLETO DE GESTIÓN MULTIMEDIA PARA DUEÑOS:
# - SUBIDA DE FOTOS, VIDEOS Y AUDIOS A MONGODB GRIDFS.
# - LISTADO Y ELIMINACIÓN DESDE EL PANEL DEL DUEÑO.
# - VISUALIZACIÓN PÚBLICA EN LA PÁGINA DEL LOCAL.
#
# ADEMÁS, SE HA CORREGIDO LA RUTA /feedback PARA QUE CUALQUIER ROL
# (CLIENTE, DUEÑO, EMPLEADO, ADMIN) PUEDA ENVIAR FEEDBACK SIN
# NECESIDAD DE TENER UN REGISTRO EN LA TABLA `usuarios`.
#
# FINALMENTE, SE HA MODIFICADO LA GESTIÓN DE FAVORITOS PARA INCLUIR
# EL CAMPO `tipo_usuario`, DE MODO QUE CADA ROL PUEDA TENER SUS
# PROPIOS FAVORITOS DE MANERA INDEPENDIENTE.
# ========================================================================

# ========================================================================
# BLOQUE: IMPORTACIÓN DE LIBRERÍAS
# ========================================================================
# SE IMPORTAN TODOS LOS MÓDULOS NECESARIOS PARA EL FUNCIONAMIENTO DE LA
# APLICACIÓN. CADA MÓDULO APORTA FUNCIONALIDADES ESPECÍFICAS.
# ========================================================================

# Flask: marco principal para la aplicación web.
from flask import Flask, render_template, request, redirect, session, jsonify, url_for, abort, send_file, flash

# os: para interactuar con el sistema operativo (rutas, variables de entorno, etc.).
import os
import secrets
import sqlite3
import uuid

# time: para manejar tiempos y fechas (usado para generar nombres únicos).
import time

# random y string: para generar códigos aleatorios y cadenas (como contraseñas temporales).
import random
import string

# secure_filename: para sanitizar nombres de archivos subidos.
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

# wraps: para mantener la información de la función original al usar decoradores.
from functools import wraps

# timedelta: para manejar duraciones de tiempo (como el tiempo de vida de la sesión).
from datetime import datetime, timedelta

# json: para trabajar con datos en formato JSON.
import json

# flask_mail: para enviar correos electrónicos desde la aplicación.
class Message:
    def __init__(self, subject='', recipients=None, body=''):
        self.subject = subject
        self.recipients = recipients or []
        self.body = body


class Mail:
    def __init__(self, app=None):
        self.app = app

    def send(self, message):
        print('Correo omitido en entorno gratuito:', message.subject)

# PIL (Pillow): para procesar imágenes (redimensionar, convertir, etc.).
from PIL import Image

# io: para manejar flujos de datos en memoria (BytesIO).
import io

# load_dotenv: para cargar variables de entorno desde un archivo .env.
def load_dotenv():
    return False

class MySQLdb:
    IntegrityError = sqlite3.IntegrityError


class bson:
    @staticmethod
    def ObjectId(value):
        return str(value)

# ========================================================================
# BLOQUE: CARGA DE VARIABLES DE ENTORNO
# ========================================================================
# SE CARGAN LAS VARIABLES DE ENTORNO DESDE EL ARCHIVO .env PARA
# CONFIGURAR LA APLICACIÓN DE FORMA SEGURA Y FLEXIBLE.
# ========================================================================

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_PATH = os.environ.get('SQLITE_PATH', os.path.join(BASE_DIR, 'instance', 'blooma.db'))


class SQLiteCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, params=()):
        sql = sql.replace('%s', '?').replace('CURDATE()', "DATE('now')").replace(' FOR UPDATE', '')
        command = sql.strip().upper()
        if command == 'START TRANSACTION':
            if not self._cursor.connection.in_transaction:
                self._cursor.connection.execute('BEGIN')
            return self
        if command == 'ROLLBACK':
            if self._cursor.connection.in_transaction:
                self._cursor.connection.rollback()
            return self
        if command == 'COMMIT':
            self._cursor.connection.commit()
            return self
        self._cursor.execute(sql, params or ())
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def close(self):
        self._cursor.close()


class SQLiteMySQL:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
        self._conn.execute('PRAGMA journal_mode=WAL')
        self._conn.execute('PRAGMA foreign_keys=ON')
        self.connection = self
        self._crear_schema()

    def cursor(self):
        return SQLiteCursor(self._conn.cursor())

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def _crear_schema(self):
        self._conn.executescript('''
        CREATE TABLE IF NOT EXISTS administradores (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, correo TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL, telefono TEXT, nivel_acceso TEXT DEFAULT 'superadmin',
            estado TEXT DEFAULT 'activo', created_at TEXT DEFAULT CURRENT_TIMESTAMP, foto_perfil TEXT
        );
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, correo TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL, fecha_nacimiento TEXT, telefono TEXT, direccion TEXT,
            documento_identidad TEXT, foto_perfil TEXT, estado TEXT DEFAULT 'activo',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS duenos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, correo TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL, telefono TEXT, direccion TEXT, documento_identidad TEXT,
            estado TEXT DEFAULT 'activo', created_at TEXT DEFAULT CURRENT_TIMESTAMP, foto_perfil TEXT
        );
        CREATE TABLE IF NOT EXISTS locales (
            id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT NOT NULL UNIQUE, nombre TEXT,
            descripcion TEXT, ubicacion TEXT, categoria TEXT, dueno_id INTEGER NOT NULL,
            dias_stock TEXT, anuncios TEXT, ofertas TEXT, imagen_fondo TEXT,
            FOREIGN KEY(dueno_id) REFERENCES duenos(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS empleados (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, correo TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL, telefono TEXT, local_id INTEGER NOT NULL, puesto TEXT NOT NULL,
            rol TEXT DEFAULT 'empleado', salario NUMERIC DEFAULT 0, fecha_contratacion TEXT DEFAULT CURRENT_DATE,
            foto_perfil TEXT, FOREIGN KEY(local_id) REFERENCES locales(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, precio NUMERIC NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0, local_id INTEGER NOT NULL,
            FOREIGN KEY(local_id) REFERENCES locales(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS carrito (
            id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER NOT NULL, producto_id INTEGER NOT NULL,
            cantidad INTEGER NOT NULL DEFAULT 1, fecha_agregado TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(usuario_id, producto_id)
        );
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER NOT NULL, total NUMERIC NOT NULL,
            fecha TEXT DEFAULT CURRENT_TIMESTAMP, codigo TEXT NOT NULL UNIQUE, estado TEXT DEFAULT 'pendiente',
            local_id INTEGER NOT NULL, fecha_recogida TEXT, hora_recogida TEXT
        );
        CREATE TABLE IF NOT EXISTS detalle_pedido (
            id INTEGER PRIMARY KEY AUTOINCREMENT, pedido_id INTEGER NOT NULL, producto_id INTEGER NOT NULL,
            cantidad INTEGER NOT NULL, precio_unitario NUMERIC NOT NULL
        );
        CREATE TABLE IF NOT EXISTS favoritos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER NOT NULL, tipo_usuario TEXT NOT NULL,
            producto_id INTEGER NOT NULL, fecha_agregado TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(usuario_id, tipo_usuario, producto_id)
        );
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER NOT NULL, mensaje TEXT NOT NULL,
            fecha TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS proveedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nombre TEXT NOT NULL, contacto_nombre TEXT,
            telefono TEXT, correo TEXT, direccion TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS solicitudes_dueno (
            id INTEGER PRIMARY KEY AUTOINCREMENT, dueno_id INTEGER NOT NULL, nombre_local TEXT NOT NULL,
            ubicacion TEXT NOT NULL, descripcion TEXT, documento_path TEXT DEFAULT '',
            estado_solicitud TEXT DEFAULT 'pendiente', fecha_solicitud TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS solicitudes_empleado (
            id INTEGER PRIMARY KEY AUTOINCREMENT, usuario_id INTEGER NOT NULL, local_id INTEGER NOT NULL,
            puesto TEXT, documento_path TEXT, mensaje TEXT, estado_solicitud TEXT DEFAULT 'pendiente',
            fecha_solicitud TEXT DEFAULT CURRENT_TIMESTAMP
        );
        ''')
        if not self._conn.execute('SELECT 1 FROM usuarios LIMIT 1').fetchone():
            clave = generate_password_hash('demo123')
            self._conn.execute('INSERT INTO administradores (nombre,correo,password,telefono) VALUES (?,?,?,?)',
                               ('Administración Demo', 'admin@demo.local', clave, '5550000001'))
            self._conn.execute('INSERT INTO usuarios (nombre,correo,password,fecha_nacimiento,telefono,direccion,estado) VALUES (?,?,?,?,?,?,?)',
                               ('Cliente Demo', 'cliente@demo.local', clave, '2000-01-01', '5550000002', 'Dirección de demostración', 'activo'))
            duenos = [
                ('Cocina Demo', 'dueno@demo.local', clave, '5550000010', 'Pasillo A', 'DEMO-01', 'activo'),
                ('Belleza Demo', 'belleza@demo.local', clave, '5550000011', 'Pasillo B', 'DEMO-02', 'activo'),
                ('Mascotas Demo', 'mascotas@demo.local', clave, '5550000012', 'Pasillo C', 'DEMO-03', 'activo'),
                ('Dulcería Demo', 'dulceria@demo.local', clave, '5550000013', 'Pasillo D', 'DEMO-04', 'activo'),
            ]
            self._conn.executemany('INSERT INTO duenos (nombre,correo,password,telefono,direccion,documento_identidad,estado) VALUES (?,?,?,?,?,?,?)', duenos)
            locales = [
                ('LOC-COM-01', 'Cocina del Bosque', 'Comida mexicana preparada al momento.', 'Pasillo A, Local 12', 'comida', 1, 'Diario'),
                ('LOC-BEL-01', 'Belleza Frambuesa', 'Cosméticos y cuidado personal.', 'Pasillo B, Local 4', 'cosmeticos', 2, 'Martes y jueves'),
                ('LOC-MAS-01', 'Mascotas Arándano', 'Alimento y accesorios para mascotas.', 'Pasillo C, Local 8', 'mascotas', 3, 'Lunes y viernes'),
                ('LOC-DUL-01', 'Dulcería Cereza', 'Dulces, botanas y artículos para fiestas.', 'Pasillo D, Local 6', 'dulceria', 4, 'Miércoles y sábado'),
            ]
            self._conn.executemany('INSERT INTO locales (codigo,nombre,descripcion,ubicacion,categoria,dueno_id,dias_stock) VALUES (?,?,?,?,?,?,?)', locales)
            productos = [
                ('Comida corrida', 75, 40, 1), ('Chilaquiles con huevo', 55, 25, 1), ('Mole poblano con arroz', 80, 18, 1),
                ('Agua micelar', 115, 12, 2), ('Labial líquido', 95, 20, 2), ('Máscara para pestañas', 185, 15, 2),
                ('Alimento para perro', 240, 14, 3), ('Correa para mascota', 120, 10, 3), ('Juguete para gato', 85, 16, 3),
                ('Caja de chocolates', 65, 30, 4), ('Dulces surtidos', 45, 50, 4), ('Botana familiar', 55, 24, 4),
            ]
            self._conn.executemany('INSERT INTO productos (nombre,precio,stock,local_id) VALUES (?,?,?,?)', productos)
            self._conn.execute('INSERT INTO empleados (nombre,correo,password,telefono,local_id,puesto) VALUES (?,?,?,?,?,?)',
                               ('Empleado Demo', 'empleado@demo.local', clave, '5550000020', 1, 'Cajero'))
            self._conn.executemany('INSERT INTO proveedores (nombre,contacto_nombre,telefono,correo,direccion) VALUES (?,?,?,?,?)', [
                ('Proveedor Frutal', 'Contacto Demo', '5550000030', 'proveedor@demo.local', 'Centro de distribución'),
                ('Insumos del Mercado', 'Ventas Demo', '5550000031', 'insumos@demo.local', 'Zona comercial'),
            ])
        self._conn.commit()


class LocalGridRecord(io.BytesIO):
    def __init__(self, file_id, data, metadata):
        super().__init__(data)
        self._id = file_id
        self.filename = metadata.get('filename', 'archivo')
        self.content_type = metadata.get('content_type', 'application/octet-stream')
        self.uploadDate = datetime.now()
        self.length = len(data)
        for key, value in metadata.items():
            setattr(self, key, value)


class LocalGridQuery(list):
    def sort(self, *args):
        return self

    def limit(self, value):
        return LocalGridQuery(self[:value])


class LocalGridFS:
    def __init__(self):
        self._files = {}

    def put(self, data, **metadata):
        raw = data.read() if hasattr(data, 'read') else bytes(data)
        file_id = uuid.uuid4().hex
        self._files[file_id] = LocalGridRecord(file_id, raw, metadata)
        return file_id

    def find(self, query):
        return LocalGridQuery([
            record for record in self._files.values()
            if all(getattr(record, key, None) == value for key, value in query.items())
        ])

    def find_one(self, query):
        rows = self.find(query)
        return rows[0] if rows else None

    def get(self, file_id):
        record = self._files[str(file_id)]
        record.seek(0)
        return record

    def delete(self, file_id):
        self._files.pop(str(file_id), None)

    def exists(self, file_id):
        return str(file_id) in self._files


class DummyIndex:
    def create_index(self, *args, **kwargs):
        return None


class DummyMongoDB:
    class _FS:
        files = DummyIndex()
    fs = _FS()


def password_valido(guardado, enviado):
    try:
        return check_password_hash(guardado, enviado)
    except (ValueError, TypeError):
        return secrets.compare_digest(str(guardado), str(enviado))
# Se cargan las variables de entorno desde el archivo .env en el directorio raíz.

# ========================================================================
# BLOQUE: CREACIÓN DE LA APLICACIÓN FLASK
# ========================================================================
# SE INSTANCIA LA APLICACIÓN FLASK CON EL NOMBRE DEL MÓDULO ACTUAL.
# ========================================================================

app = Flask(__name__)
# Se crea una instancia de la clase Flask. El parámetro __name__ permite
# a Flask localizar la ubicación de los templates y archivos estáticos.

# ========================================================================
# BLOQUE: CONFIGURACIÓN DE CLAVE SECRETA Y SESIÓN
# ========================================================================
# SE ESTABLECE LA CLAVE SECRETA PARA SESIONES Y COOKIES, Y LA DURACIÓN
# DE LA SESIÓN PERMANENTE.
# ========================================================================

app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
# Se obtiene la clave secreta de las variables de entorno (SECRET_KEY).
# Si no existe, se usa un valor por defecto. Esta clave es usada para
# firmar las cookies de sesión y protegerlas contra manipulaciones.

app.permanent_session_lifetime = timedelta(hours=1)
# Define que la sesión del usuario durará 1 hora antes de expirar.
# La sesión se considera "permanente" y se renovará automáticamente.

# ========================================================================
# BLOQUE: CONFIGURACIÓN DE MYSQL
# ========================================================================
# SE CONFIGURA LA CONEXIÓN A LA BASE DE DATOS MYSQL USANDO VARIABLES
# DE ENTORNO PARA MAYOR SEGURIDAD.
# ========================================================================

app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'localhost')
# Se establece el host de MySQL desde las variables de entorno.
# Si no existe, se usa 'localhost' como valor por defecto.

app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'root')
# Se establece el usuario de MySQL desde las variables de entorno.
# Por defecto se usa 'root'.

app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', '')
# Se establece la contraseña de MySQL desde las variables de entorno.
# Por defecto es una cadena vacía (sin contraseña).

app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'conecta_mercado360')
# Se establece el nombre de la base de datos MySQL.
# Por defecto se usa 'conecta_mercado360'.

mysql = SQLiteMySQL(SQLITE_PATH)
# Se crea una instancia de MySQL asociada a la aplicación Flask.
# Esta instancia se usará para ejecutar consultas SQL.

# ========================================================================
# BLOQUE: CONFIGURACIÓN DE MONGODB
# ========================================================================
# SE CONFIGURA LA CONEXIÓN A MONGODB PARA ALMACENAR ARCHIVOS MULTIMEDIA
# USANDO GRIDFS. TAMBIÉN SE CREAN ÍNDICES PARA BÚSQUEDAS RÁPIDAS.
# ========================================================================

MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
# Se obtiene la URI de MongoDB desde las variables de entorno.
# Si no existe, se usa la URI local por defecto (mongodb://localhost:27017/).

MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME', 'blooma_images')
# Se obtiene el nombre de la base de datos MongoDB desde las variables de entorno.
# Por defecto se usa 'blooma_images'.

mongo_client = None
# Se crea un cliente de MongoDB usando la URI proporcionada.
# Este cliente se conecta al servidor de MongoDB.

mongo_db = DummyMongoDB()
# Se selecciona la base de datos específica dentro del cliente MongoDB.
# Si la base de datos no existe, se creará automáticamente al insertar datos.

fs = LocalGridFS()
# Se inicializa GridFS para manejar archivos en MongoDB.
# GridFS permite almacenar archivos grandes (como imágenes, videos y audios)
# dividiéndolos en fragmentos (chunks).

try:
    # Índices para búsquedas rápidas por colección y ID
    # Se crea un índice compuesto en la colección 'fs.files' para acelerar
    # las consultas por coleccion e id_coleccion.
    mongo_db.fs.files.create_index([("coleccion", 1), ("id_coleccion", 1)])
    # "coleccion" y "id_coleccion" son campos personalizados que usamos
    # para asociar cada archivo a un objeto (producto, local, usuario, etc.).
    # El valor "1" indica orden ascendente en el índice.

    # Se crea un índice por fecha de subida en orden descendente.
    # Esto permite obtener los archivos más recientes rápidamente.
    mongo_db.fs.files.create_index("uploadDate", -1)
    # El valor "-1" indica orden descendente (más reciente primero).

except Exception as e:
    # Si los índices ya existen o hay otro error, se imprime un mensaje.
    # Esto no interrumpe el flujo de la aplicación.
    print("Índices MongoDB ya existentes o error:", e)

# ========================================================================
# BLOQUE: CONFIGURACIÓN DEL CORREO (FLASK-MAIL)
# ========================================================================
# SE CONFIGURA EL SERVIDOR SMTP DE GMAIL PARA ENVIAR CORREOS
# DESDE LA APLICACIÓN. SE USAN VARIABLES DE ENTORNO PARA LAS CREDENCIALES.
# ========================================================================

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
# Servidor SMTP de Gmail para enviar correos electrónicos.

app.config['MAIL_PORT'] = 587
# Puerto TLS para Gmail (587 es el puerto estándar para STARTTLS).

app.config['MAIL_USE_TLS'] = True
# Habilita TLS (Transport Layer Security) para la conexión segura con el servidor.

app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
# Cuenta de correo desde la que se enviarán los mensajes.
# Esta es la dirección de correo de la aplicación.

app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
# Contraseña de aplicación generada para Gmail.
# NO es la contraseña personal del correo; es una contraseña de aplicación
# que Gmail genera para permitir el acceso desde aplicaciones externas.

app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')
# Remitente por defecto para todos los correos enviados desde la aplicación.

mail = Mail(app)
# Se crea una instancia de Mail asociada a la aplicación Flask.
# Esta instancia se usará para enviar mensajes de correo.

# ========================================================================
# BLOQUE: CONFIGURACIÓN DE SUBIDA DE ARCHIVOS
# ========================================================================
# SE DEFINE LA CARPETA DONDE SE GUARDARÁN LOS ARCHIVOS SUBIDOS,
# LAS EXTENSIONES PERMITIDAS Y EL TAMAÑO MÁXIMO DE CARGA.
# ========================================================================

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'perfiles')
# Carpeta donde se guardarán las fotos de perfil en el sistema de archivos local.
# Esta ruta es relativa al directorio raíz de la aplicación.

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
# Conjunto de extensiones de archivo permitidas para subida.
# Solo se aceptarán archivos con estas extensiones.

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Se asigna la carpeta de subida a la configuración de Flask para que
# pueda ser accedida desde otras partes de la aplicación.

app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024
# Se limita el tamaño máximo de cada solicitud a 50 megabytes.
# Esto evita que los usuarios suban archivos extremadamente grandes
# que podrían saturar el servidor.

# ========================================================================
# FUNCIÓN: allowed_file
# ========================================================================
# DESCRIPCIÓN: VERIFICA SI UN ARCHIVO TIENE UNA EXTENSIÓN PERMITIDA.
# PARÁMETROS:
#   - filename: NOMBRE DEL ARCHIVO A VERIFICAR.
# RETORNA: TRUE SI LA EXTENSIÓN ES PERMITIDA, FALSE EN CASO CONTRARIO.
# ========================================================================

def allowed_file(filename):
    # Verifica si el nombre del archivo contiene un punto y la extensión
    # está en el conjunto de extensiones permitidas.
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    # rsplit('.', 1) separa el nombre en dos partes: el nombre y la extensión.
    # El índice [1] obtiene la extensión. Se convierte a minúsculas para
    # hacer la comparación insensible a mayúsculas/minúsculas.

# ========================================================================
# FUNCIONES PARA GUARDAR Y OBTENER IMÁGENES EN MONGODB (GRIDFS)
# ========================================================================

# ========================================================================
# FUNCIÓN: guardar_archivo
# ========================================================================
# DESCRIPCIÓN: GUARDA UN ARCHIVO EN MONGODB GRIDFS ASOCIADO A UNA
# COLECCIÓN Y UN ID DE OBJETO. SI ES UNA IMAGEN, LA COMPRIME A JPEG.
# PARÁMETROS:
#   - coleccion: NOMBRE DE LA COLECCIÓN (EJ. 'producto', 'local', 'usuario').
#   - id_objeto: ID DEL OBJETO AL QUE PERTENECE EL ARCHIVO.
#   - file_storage: OBJETO DE TIPO FileStorage (ARCHIVO SUBIDO).
#   - comprimir: BOOLEANO QUE INDICA SI SE DEBE COMPRIMIR LA IMAGEN.
# RETORNA: EL ID DEL ARCHIVO GUARDADO COMO CADENA, O NONE SI FALLA.
# ========================================================================

def guardar_archivo(coleccion, id_objeto, file_storage, comprimir=True):
    # Si no se proporciona un archivo, se retorna None.
    if not file_storage:
        return None

    # Si se indica comprimir y el archivo es una imagen, se procesa.
    if comprimir and file_storage.content_type and 'image' in file_storage.content_type:
        try:
            img = Image.open(file_storage.stream)
            # Se abre la imagen desde el flujo de datos (stream) del archivo.
            # Esto permite leer la imagen sin necesidad de guardarla primero.

            # Si la imagen tiene transparencia (RGBA, LA) o modo paleta (P),
            # se convierte a RGB para evitar problemas al guardar como JPEG.
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
                # El modo RGB es el estándar para imágenes sin transparencia.

            # Se redimensiona la imagen a un tamaño máximo de 1024x1024
            # usando el filtro LANCZOS que ofrece alta calidad.
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            # thumbnail() mantiene la relación de aspecto original.

            output = io.BytesIO()
            # Se crea un buffer de bytes en memoria para almacenar la imagen procesada.
            # Esto evita guardar el archivo en el sistema de archivos.

            # Se guarda la imagen en formato JPEG con calidad 80 y optimización.
            # La calidad 80 es un buen equilibrio entre tamaño y calidad.
            img.save(output, format='JPEG', quality=80, optimize=True)
            # optimize=True intenta reducir aún más el tamaño del archivo.

            output.seek(0)
            # Se posiciona el puntero al inicio del buffer para su lectura.

            data = output
            # Los datos procesados son el contenido del buffer.

            content_type = 'image/jpeg'
            # Se establece el tipo MIME a JPEG, ya que se ha convertido.

            # Se genera un nombre de archivo seguro, cambiando la extensión a .jpg.
            filename = secure_filename(file_storage.filename).rsplit('.', 1)[0] + '.jpg'
            # secure_filename elimina caracteres peligrosos y normaliza el nombre.

        except Exception as e:
            # Si falla el procesamiento de imagen, se guarda el archivo original.
            file_storage.stream.seek(0)
            # Se reposiciona el puntero del archivo original al inicio.

            data = file_storage.stream
            # Se usa el flujo original.

            content_type = file_storage.content_type
            # Se conserva el tipo MIME original.

            filename = secure_filename(file_storage.filename)
            # Se usa el nombre original sanitizado.
    else:
        # Si no es imagen o no se comprime, se guarda tal cual.
        data = file_storage.stream
        # Flujo original.

        content_type = file_storage.content_type
        # Tipo MIME original.

        filename = secure_filename(file_storage.filename)
        # Nombre sanitizado.

    # Eliminar archivo anterior si existe (para mantener uno por objeto)
    # Busca cualquier archivo existente con la misma colección e ID de objeto.
    for grid_out in fs.find({"coleccion": coleccion, "id_coleccion": id_objeto}):
        # find() devuelve un cursor con todos los archivos que coinciden.
        fs.delete(grid_out._id)
        # Se elimina cada uno de ellos. Esto asegura que solo haya un archivo
        # por objeto (sobrescribe el anterior).

    # Guardar el nuevo archivo en GridFS.
    file_id = fs.put(
        # Datos del archivo (puede ser un flujo o bytes).
        data,
        # Nombre del archivo.
        filename=filename,
        # Campo personalizado: colección.
        coleccion=coleccion,
        # Campo personalizado: ID del objeto.
        id_coleccion=id_objeto,
        # Tipo MIME.
        content_type=content_type
    )
    # Retorna el ID del archivo como cadena para poder referenciarlo después.
    return str(file_id)

# ========================================================================
# FUNCIÓN: obtener_archivo
# ========================================================================
# DESCRIPCIÓN: OBTIENE EL ARCHIVO MÁS RECIENTE ASOCIADO A UNA COLECCIÓN
# Y UN ID DE OBJETO.
# PARÁMETROS:
#   - coleccion: NOMBRE DE LA COLECCIÓN.
#   - id_objeto: ID DEL OBJETO.
# RETORNA: EL OBJETO GridOut DEL ARCHIVO, O NONE SI NO EXISTE.
# ========================================================================

def obtener_archivo(coleccion, id_objeto):
    # Busca el archivo más reciente asociado a la colección e ID de objeto.
    # find() devuelve un cursor; sort() ordena por fecha de subida descendente;
    # limit(1) toma solo el primero (el más reciente).
    for grid_out in fs.find({"coleccion": coleccion, "id_coleccion": id_objeto}).sort("uploadDate", -1).limit(1):
        # Si existe, retorna el objeto GridOut del archivo.
        return grid_out
    # Si no hay archivo, retorna None.
    return None

# ========================================================================
# FUNCIÓN: eliminar_archivo
# ========================================================================
# DESCRIPCIÓN: ELIMINA TODOS LOS ARCHIVOS ASOCIADOS A UNA COLECCIÓN Y ID.
# PARÁMETROS:
#   - coleccion: NOMBRE DE LA COLECCIÓN.
#   - id_objeto: ID DEL OBJETO.
# ========================================================================

def eliminar_archivo(coleccion, id_objeto):
    # Elimina todos los archivos asociados a la colección e ID de objeto.
    for grid_out in fs.find({"coleccion": coleccion, "id_coleccion": id_objeto}):
        # Itera sobre todos los archivos encontrados.
        fs.delete(grid_out._id)
        # Elimina cada uno.

# ========================================================================
# FUNCIÓN: tiene_imagen
# ========================================================================
# DESCRIPCIÓN: VERIFICA SI EXISTE AL MENOS UN ARCHIVO PARA LA COLECCIÓN E ID.
# PARÁMETROS:
#   - coleccion: NOMBRE DE LA COLECCIÓN.
#   - id_objeto: ID DEL OBJETO.
# RETORNA: TRUE SI EXISTE UN ARCHIVO, FALSE EN CASO CONTRARIO.
# ========================================================================

def tiene_imagen(coleccion, id_objeto):
    # Retorna True si existe al menos un archivo para la colección e ID.
    # Usa find_one() para verificar existencia de forma eficiente.
    return fs.find_one({"coleccion": coleccion, "id_coleccion": id_objeto}) is not None
    # find_one() devuelve el primer documento que coincide, o None si no hay.

# ========================================================================
# FUNCIONES PARA MULTIMEDIA (FOTOS, VIDEOS, AUDIOS) EN GRIDFS
# ========================================================================

# Diccionario que define qué tipos MIME son aceptables para cada categoría.
# Esto permite validar que el archivo subido corresponda al tipo declarado.
ALLOWED_MIME_TYPES = {
    'foto': ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/jpg'],
    'video': ['video/mp4', 'video/webm', 'video/avi', 'video/mov', 'video/quicktime'],
    'audio': ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp3', 'audio/aac']
}

# ========================================================================
# FUNCIÓN: guardar_multimedia
# ========================================================================
# DESCRIPCIÓN: GUARDA UN ARCHIVO MULTIMEDIA EN GRIDFS ASOCIADO A UN LOCAL.
# SOPORTA FOTOS (COMPRIME Y CONVIERTE A JPEG), VIDEOS Y AUDIOS (SIN MODIFICAR).
# PARÁMETROS:
#   - local_id: ID DEL LOCAL AL QUE PERTENECE EL ARCHIVO.
#   - file_storage: OBJETO FileStorage DEL ARCHIVO SUBIDO.
#   - tipo: 'foto', 'video' O 'audio'.
#   - descripcion: TEXTO DESCRIPTIVO OPCIONAL.
# RETORNA: EL ID DEL ARCHIVO GUARDADO COMO CADENA, O NONE SI FALLA.
# ========================================================================

def guardar_multimedia(local_id, file_storage, tipo, descripcion=""):
    # Si no hay archivo, retorna None.
    if not file_storage:
        return None

    # Leer el archivo completo en memoria (hasta 50 MB, controlado por MAX_CONTENT_LENGTH)
    try:
        data_bytes = file_storage.read()
        # Lee todos los bytes del archivo y los almacena en un objeto bytes.
    except Exception as e:
        # Si hay error al leer, se imprime el error y retorna None.
        print(f"Error al leer archivo: {e}")
        return None

    # Si no se leyeron datos, retorna None.
    if not data_bytes:
        return None

    content_type = file_storage.content_type
    # Tipo MIME del archivo (ej. 'image/jpeg', 'video/mp4').

    original_filename = secure_filename(file_storage.filename)
    # Nombre del archivo sanitizado para evitar caracteres peligrosos.

    # Validar que el tipo MIME coincida con el tipo declarado.
    if tipo in ALLOWED_MIME_TYPES:
        # Si el tipo está en el diccionario.
        if content_type not in ALLOWED_MIME_TYPES[tipo]:
            # Si el tipo MIME no está permitido para esa categoría, imprime error y retorna None.
            print(f"Tipo MIME {content_type} no permitido para {tipo}")
            return None

    # Para fotos, comprimir y convertir a JPEG.
    if tipo == 'foto' and content_type and 'image' in content_type:
        # Si es foto y es una imagen.
        try:
            # Abre la imagen desde los bytes usando PIL.
            img = Image.open(io.BytesIO(data_bytes))

            # Si la imagen tiene transparencia o modo paleta, se convierte a RGB.
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')

            # Redimensiona a un tamaño máximo de 1024x1024 manteniendo relación de aspecto.
            img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)

            # Crea un buffer en memoria para guardar la imagen procesada.
            output = io.BytesIO()

            # Guarda la imagen como JPEG con calidad 80 y optimización.
            img.save(output, format='JPEG', quality=80, optimize=True)

            # Obtiene los bytes de la imagen procesada.
            data_bytes = output.getvalue()

            # Actualiza el tipo MIME a JPEG.
            content_type = 'image/jpeg'

            # Cambia la extensión del nombre a .jpg.
            filename = original_filename.rsplit('.', 1)[0] + '.jpg'

        except Exception as e:
            # Si falla la compresión, se guarda el original.
            print(f"Error al procesar imagen: {e}")
            filename = original_filename
    else:
        # Para videos y audios, guardar tal cual.
        filename = original_filename

    # Guardar en GridFS.
    try:
        file_id = fs.put(
            data_bytes,               # Datos en bytes.
            filename=filename,        # Nombre del archivo.
            content_type=content_type,# Tipo MIME.
            local_id=local_id,        # ID del local al que pertenece.
            tipo=tipo,                # Tipo de multimedia (foto, video, audio).
            descripcion=descripcion,  # Descripción opcional.
            coleccion='multimedia',   # Campo fijo para identificar estos archivos.
            id_coleccion=local_id     # También se guarda el ID del local para compatibilidad.
        )
        # Retorna el ID del archivo como cadena.
        return str(file_id)
    except Exception as e:
        # Si hay error al guardar, imprime y retorna None.
        print(f"Error al guardar en GridFS: {e}")
        return None

# ========================================================================
# FUNCIÓN: listar_multimedia
# ========================================================================
# DESCRIPCIÓN: LISTA LOS ARCHIVOS MULTIMEDIA ASOCIADOS A UN LOCAL.
# PARÁMETROS:
#   - local_id: ID DEL LOCAL.
#   - limit: NÚMERO MÁXIMO DE ARCHIVOS A RETORNAR (POR DEFECTO 100).
# RETORNA: UNA LISTA DE DICCIONARIOS CON LOS METADATOS DE CADA ARCHIVO.
# ========================================================================

def listar_multimedia(local_id, limit=100):
    # Lista vacía para almacenar los metadatos.
    files = []

    # Busca archivos con coleccion="multimedia" y id_coleccion=local_id.
    # Ordena por fecha de subida descendente y limita a 'limit' resultados.
    for grid_out in fs.find({"coleccion": "multimedia", "id_coleccion": local_id}).sort("uploadDate", -1).limit(limit):
        # Agrega un diccionario con los metadatos del archivo.
        files.append({
            'file_id': str(grid_out._id),           # ID del archivo como cadena.
            'filename': grid_out.filename,          # Nombre del archivo.
            'content_type': grid_out.content_type,  # Tipo MIME.
            'tipo': grid_out.tipo if hasattr(grid_out, 'tipo') else 'foto',
            # Tipo, por defecto 'foto' si no existe el atributo.
            'descripcion': grid_out.descripcion if hasattr(grid_out, 'descripcion') else '',
            # Descripción, vacía si no existe.
            'upload_date': grid_out.uploadDate,     # Fecha de subida.
            'size': grid_out.length                 # Tamaño en bytes.
        })
    # Retorna la lista de archivos.
    return files

# ========================================================================
# FUNCIÓN: eliminar_multimedia
# ========================================================================
# DESCRIPCIÓN: ELIMINA UN ARCHIVO DE GRIDFS DADO SU ID (STRING).
# PARÁMETROS:
#   - file_id_str: ID DEL ARCHIVO COMO CADENA.
# RETORNA: TRUE SI SE ELIMINÓ, FALSE EN CASO CONTRARIO.
# ========================================================================

def eliminar_multimedia(file_id_str):
    # Intenta eliminar el archivo.
    try:
        # Convierte el string a ObjectId de MongoDB.
        file_id = bson.ObjectId(file_id_str)

        # Verifica si el archivo existe en GridFS.
        if fs.exists(file_id):
            # Si existe, lo elimina.
            fs.delete(file_id)
            # Retorna True indicando éxito.
            return True
        # Si no existe, retorna False.
        return False
    except:
        # Si ocurre cualquier excepción (ID inválido, error de conexión, etc.), retorna False.
        return False

# ========================================================================
# FUNCIÓN AUXILIAR: generar_codigo_pedido
# ========================================================================
# DESCRIPCIÓN: GENERA UN CÓDIGO ALEATORIO DE 8 CARACTERES PARA PEDIDOS.
# RETORNA: UN STRING DE 8 CARACTERES (LETRAS MAYÚSCULAS Y DÍGITOS).
# ========================================================================

def generar_codigo_pedido():
    # Genera un código aleatorio de 8 caracteres.
    # string.ascii_uppercase son letras mayúsculas de la A a la Z.
    # string.digits son dígitos del 0 al 9.
    # random.choices elige 8 caracteres al azar con reemplazo.
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# ========================================================================
# DECORADOR: login_required
# ========================================================================
# DESCRIPCIÓN: DECORADOR PARA REQUERIR INICIO DE SESIÓN EN UNA RUTA.
# SI EL USUARIO NO TIENE SESIÓN ACTIVA, SE REDIRIGE A /login CON UN MENSAJE.
# ========================================================================

def login_required(f):
    # El decorador recibe una función f como argumento.
    @wraps(f)
    # wraps mantiene el nombre y la documentación de la función original.
    def wrapper(*args, **kwargs):
        # Función envolvente que se ejecutará en lugar de la original.
        if 'usuario_id' not in session:
            # Si no hay usuario en sesión (no autenticado).
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            # Muestra un mensaje de advertencia usando flash.
            return redirect('/login')
            # Redirige al usuario a la página de login.
        # Si está autenticado, ejecuta la función original con sus argumentos.
        return f(*args, **kwargs)
    # Retorna la función envolvente.
    return wrapper

# ========================================================================
# DECORADOR: rol_requerido
# ========================================================================
# DESCRIPCIÓN: DECORADOR PARA REQUERIR UNO O MÁS ROLES ESPECÍFICOS.
# SI EL ROL DEL USUARIO NO ESTÁ EN LA LISTA PERMITIDA, SE REDIRIGE A /inicio.
# PARÁMETROS:
#   - roles: LISTA DE ROLES PERMITIDOS (EJ. ['admin', 'dueno']).
# ========================================================================

def rol_requerido(roles):
    # El decorador recibe una lista de roles permitidos.
    def decorator(f):
        # Decorador interno que recibe la función.
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Función envolvente.
            if 'rol' not in session or session['rol'] not in roles:
                # Si no hay rol en sesión o el rol no está en la lista permitida.
                flash('No tienes permiso para acceder a esta sección.', 'danger')
                # Muestra un mensaje de peligro.
                return redirect('/inicio')
                # Redirige al inicio.
            # Si tiene permiso, ejecuta la función original.
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ========================================================================
# BLOQUE: VERIFICACIÓN DE CONEXIÓN A BASE DE DATOS (AL INICIAR)
# ========================================================================
# DENTRO DEL CONTEXTO DE LA APLICACIÓN, SE PRUEBA LA CONEXIÓN A MYSQL.
# ========================================================================

with app.app_context():
    # Dentro del contexto de la aplicación (necesario para acceder a mysql).
    try:
        # Obtiene un cursor de MySQL para ejecutar consultas.
        cursor = mysql.connection.cursor()
        # Ejecuta una consulta simple para probar la conexión.
        cursor.execute("SELECT 1")
        # Cierra el cursor para liberar recursos.
        cursor.close()
        # Mensaje de éxito en consola.
        print("Conexión exitosa a MySQL (conecta_mercado360)")
    except Exception as e:
        # Si hay error, muestra el mensaje en consola.
        print(f"Error de conexión a MySQL: {e}")

# ========================================================================
# FUNCIÓN: obtener_carrito_db
# ========================================================================
# DESCRIPCIÓN: OBTIENE LOS ITEMS DEL CARRITO DE UN USUARIO DESDE LA BD.
# PARÁMETROS:
#   - usuario_id: ID DEL USUARIO.
# RETORNA: UNA TUPLA (LISTA_ITEMS, TOTAL) CON LOS PRODUCTOS Y EL TOTAL.
# ========================================================================

def obtener_carrito_db(usuario_id):
    # Crea un cursor para la base de datos.
    cursor = mysql.connection.cursor()
    # Consulta que une carrito, productos y locales para obtener todos los detalles.
    cursor.execute("""
        SELECT c.producto_id, c.cantidad, p.nombre, p.precio, p.stock, p.local_id, l.nombre as local_nombre
        FROM carrito c
        JOIN productos p ON c.producto_id = p.id
        JOIN locales l ON p.local_id = l.id
        WHERE c.usuario_id = %s
    """, (usuario_id,))
    # El parámetro %s se reemplaza por usuario_id de forma segura (prevención de SQL injection).

    # Obtiene todas las filas resultantes.
    items = cursor.fetchall()
    # Cierra el cursor.
    cursor.close()

    # Lista para almacenar los items procesados.
    lista = []
    # Variable para acumular el total del carrito.
    total = 0

    # Itera sobre cada fila del resultado.
    for i in items:
        # i[0] es producto_id, i[1] es cantidad, i[2] es nombre, i[3] es precio,
        # i[4] es stock, i[5] es local_id, i[6] es local_nombre.
        producto_id = i[0]

        # Calcula el subtotal: precio * cantidad.
        subtotal = float(i[3]) * i[1]

        # Agrega un diccionario con los datos del item a la lista.
        lista.append({
            'id': producto_id,                      # ID del producto.
            'nombre': i[2],                         # Nombre del producto.
            'precio': float(i[3]),                  # Precio unitario.
            'cantidad': i[1],                       # Cantidad en el carrito.
            'stock': i[4],                          # Stock disponible del producto.
            'local_id': i[5],                       # ID del local al que pertenece.
            'local_nombre': i[6],                   # Nombre del local.
            'subtotal': subtotal,                   # Subtotal del item (precio * cantidad).
            'imagen_url': f"/imagen/producto/{producto_id}" if tiene_imagen('producto', producto_id) else None
            # URL de la imagen del producto si existe, de lo contrario None.
        })
        # Suma al total general.
        total += subtotal

    # Retorna la lista de items y el total.
    return lista, total

# ========================================================================
# FUNCIÓN: agrupar_carrito
# ========================================================================
# DESCRIPCIÓN: AGRUPA LOS ITEMS DEL CARRITO POR LOCAL.
# PARÁMETROS:
#   - usuario_id: ID DEL USUARIO.
# RETORNA: UNA TUPLA (ERROR, GRUPOS) DONDE ERROR ES NONE O UN MENSAJE,
#          Y GRUPOS ES UNA LISTA DE DICCIONARIOS AGRUPADOS POR LOCAL.
# ========================================================================

def agrupar_carrito(usuario_id):
    # Crea un cursor.
    cursor = mysql.connection.cursor()
    # Consulta similar pero incluye ubicación del local.
    cursor.execute("""
        SELECT c.producto_id, c.cantidad, p.nombre, p.precio, p.stock, p.local_id, l.nombre as local_nombre, l.ubicacion
        FROM carrito c
        JOIN productos p ON c.producto_id = p.id
        JOIN locales l ON p.local_id = l.id
        WHERE c.usuario_id = %s
    """, (usuario_id,))

    # Obtiene las filas.
    items = cursor.fetchall()
    cursor.close()

    # Si no hay items, retorna mensaje de carrito vacío y None.
    if not items:
        return "El carrito está vacío", None

    # Diccionario para agrupar por local_id.
    grupos = {}

    # Itera sobre cada item.
    for item in items:
        local_id = item[5]  # El local_id está en la posición 5.

        # Si el local no está en el diccionario, lo crea.
        if local_id not in grupos:
            grupos[local_id] = {
                'local_id': local_id,
                'local_nombre': item[6],    # Nombre del local.
                'ubicacion': item[7],       # Ubicación del local.
                'productos': [],            # Lista de productos del local.
                'subtotal_local': 0.0       # Subtotal acumulado del local.
            }

        producto_id = item[0]

        # Diccionario con los datos del producto.
        producto = {
            'id': producto_id,
            'nombre': item[2],
            'precio': float(item[3]),
            'cantidad': item[1],
            'stock': item[4],
            'subtotal': float(item[3]) * item[1],
            'imagen_url': f"/imagen/producto/{producto_id}" if tiene_imagen('producto', producto_id) else None
        }

        # Agrega el producto a la lista del local.
        grupos[local_id]['productos'].append(producto)
        # Suma al subtotal del local.
        grupos[local_id]['subtotal_local'] += producto['subtotal']

    # Retorna None (sin error) y la lista de valores del diccionario (los grupos).
    return None, list(grupos.values())

# ========================================================================
# RUTA: '/'
# ========================================================================
# DESCRIPCIÓN: PÁGINA DE CARGA (LOADING). SE MUESTRA UNA PANTALLA
# DE CARGA CON ANIMACIONES MIENTRAS LA APLICACIÓN SE PREPARA.
# ========================================================================

@app.route('/health')
def health():
    return {'status': 'ok'}, 200


@app.route('/')
# El decorador asocia la URL raíz a la función siguiente.
def inicio():
    # Renderiza la plantilla loading.html (pantalla de carga).
    return render_template('loading.html')

# ========================================================================
# RUTA: '/inicio'
# ========================================================================
# DESCRIPCIÓN: PÁGINA PRINCIPAL DEL MERCADO. MUESTRA PRODUCTOS,
# CATEGORÍAS, Y EL PANEL DEL DUEÑO SI EL USUARIO ES DUEÑO.
# ========================================================================

@app.route('/inicio')
def index():
    # Inicializa variable para almacenar datos del local si es dueño.
    local_dueno = None

    # Si el usuario está autenticado y es dueño.
    if 'usuario_id' in session and session.get('rol') == 'dueno':
        cursor = mysql.connection.cursor()
        # Obtiene el local asociado al dueño.
        cursor.execute("SELECT nombre, codigo, dias_stock FROM locales WHERE dueno_id = %s", (session['usuario_id'],))
        # Obtiene una fila (el resultado de la consulta).
        local_dueno = cursor.fetchone()
        cursor.close()

        # Si existe el local, lo convierte a diccionario.
        if local_dueno:
            local_dueno = {
                'nombre': local_dueno[0],
                'codigo': local_dueno[1],
                'dias_stock': local_dueno[2]
            }

    # Renderiza la plantilla index.html pasando el estado de autenticación
    # y los datos del local si es dueño.
    return render_template('index.html', usuario_logueado='usuario_id' in session, local_dueno=local_dueno)

# ========================================================================
# RUTA: '/login' (GET Y POST)
# ========================================================================
# DESCRIPCIÓN: PÁGINA DE INICIO DE SESIÓN. VERIFICA LAS CREDENCIALES
# DEL USUARIO EN LAS TABLAS: administradores, duenos, empleados, usuarios.
# ========================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Si la solicitud es POST (envió formulario).
    if request.method == 'POST':
        # Obtiene el correo del formulario.
        correo = request.form['correo']
        # Obtiene la contraseña del formulario.
        password = request.form['password']

        # Crea un cursor para la base de datos.
        cursor = mysql.connection.cursor()

        # --- BUSCAR EN ADMINISTRADORES ---
        cursor.execute("SELECT id, nombre, password, 'admin' as rol, estado FROM administradores WHERE correo=%s", (correo,))
        admin = cursor.fetchone()
        # Si existe admin y la contraseña coincide.
        if admin and password_valido(admin[2], password):
            # Si el estado es 'inactivo', no permite el acceso.
            if admin[4] == 'inactivo':
                flash('Cuenta de administrador inactiva.', 'danger')
                return render_template('login.html')
            # Sesión permanente.
            session.permanent = True
            # Guarda ID del admin.
            session['usuario_id'] = admin[0]
            # Guarda nombre.
            session['usuario_nombre'] = admin[1]
            # Guarda rol.
            session['rol'] = admin[3]
            # Guarda tipo de tabla.
            session['tipo_tabla'] = 'admin'
            flash('Bienvenido, Administrador.', 'success')
            return redirect('/inicio')

        # --- BUSCAR EN DUEÑOS ---
        cursor.execute("SELECT id, nombre, password, 'dueno' as rol, estado FROM duenos WHERE correo=%s", (correo,))
        dueno = cursor.fetchone()
        if dueno and password_valido(dueno[2], password):
            if dueno[4] == 'inactivo':
                flash('Cuenta de dueño inactiva. Contacta al administrador.', 'danger')
                return render_template('login.html')
            session.permanent = True
            session['usuario_id'] = dueno[0]
            session['usuario_nombre'] = dueno[1]
            session['rol'] = dueno[3]
            session['tipo_tabla'] = 'dueno'
            flash('Bienvenido, Dueño.', 'success')
            return redirect('/inicio')

        # --- BUSCAR EN EMPLEADOS ---
        cursor.execute("SELECT id, nombre, password, 'empleado' as rol, local_id FROM empleados WHERE correo=%s", (correo,))
        empleado = cursor.fetchone()
        if empleado and password_valido(empleado[2], password):
            session.permanent = True
            session['usuario_id'] = empleado[0]
            session['usuario_nombre'] = empleado[1]
            session['rol'] = empleado[3]
            session['tipo_tabla'] = 'empleado'
            session['local_id'] = empleado[4]   # Guarda el local_id del empleado.
            flash('Bienvenido, Empleado.', 'success')
            return redirect('/inicio')

        # --- BUSCAR EN CLIENTES (usuarios) ---
        cursor.execute("SELECT id, nombre, password, 'cliente' as rol, estado FROM usuarios WHERE correo=%s", (correo,))
        cliente = cursor.fetchone()
        if cliente and password_valido(cliente[2], password):
            if cliente[4] == 'inactivo':
                flash('Cuenta inactiva. Contacta al administrador.', 'danger')
                return render_template('login.html')
            session.permanent = True
            session['usuario_id'] = cliente[0]
            session['usuario_nombre'] = cliente[1]
            session['rol'] = cliente[3]
            session['tipo_tabla'] = 'cliente'
            flash('Bienvenido, Cliente.', 'success')
            return redirect('/inicio')

        # Si ninguna tabla coincide, mensaje de error.
        flash('Correo o contraseña incorrectos. Intenta de nuevo.', 'danger')
        return render_template('login.html')

    # Si es GET, muestra el formulario de login.
    return render_template('login.html')

# ========================================================================
# RUTA: '/registro' (GET Y POST)
# ========================================================================
# DESCRIPCIÓN: PÁGINA DE REGISTRO DE USUARIOS. PERMITE REGISTRARSE COMO
# CLIENTE, DUEÑO O EMPLEADO. PARA DUEÑO Y EMPLEADO SE CREAN SOLICITUDES.
# ========================================================================

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    # Si se envió el formulario (POST).
    if request.method == 'POST':
        # Obtiene los datos del formulario.
        nombre = request.form['nombre']
        correo = request.form['correo']
        password = request.form['password']
        telefono = request.form['telefono']
        fecha = request.form['fecha']
        # Tipo de cuenta (cliente, dueno, empleado), por defecto cliente.
        tipo = request.form.get('tipo_cuenta', 'cliente')
        # Dirección (opcional).
        direccion = request.form.get('direccion', '')
        # Documento de identidad (opcional).
        documento_identidad = request.form.get('documento_identidad', '')

        # Crea un cursor.
        cursor = mysql.connection.cursor()

        try:
            # ======= CASO: CLIENTE =======
            if tipo == 'cliente':
                # Inserta el nuevo cliente en la tabla usuarios.
                cursor.execute("""
                    INSERT INTO usuarios (nombre, correo, password, fecha_nacimiento, telefono, direccion, documento_identidad, estado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'activo')
                """, (nombre, correo, generate_password_hash(password), fecha, telefono, direccion, documento_identidad))
                # Confirma la transacción en la base de datos.
                mysql.connection.commit()
                flash('Registro exitoso. Ahora puedes iniciar sesión.', 'success')
                cursor.close()
                return redirect('/login')

            # ======= CASO: DUEÑO =======
            elif tipo == 'dueno':
                # Inserta en la tabla duenos con estado 'pendiente'.
                cursor.execute("""
                    INSERT INTO duenos (nombre, correo, password, telefono, documento_identidad, estado, direccion)
                    VALUES (%s, %s, %s, %s, %s, 'pendiente', %s)
                """, (nombre, correo, generate_password_hash(password), telefono, documento_identidad, direccion))
                mysql.connection.commit()
                # Obtiene el ID del nuevo dueño.
                dueno_id = cursor.lastrowid

                # Obtiene datos del local desde el formulario.
                nombre_local = request.form['nombre_local']
                ubicacion = request.form['ubicacion']
                descripcion = request.form.get('descripcion', '')

                # Manejo del documento (archivo subido).
                documento_path = None
                if 'documento' in request.files:
                    file = request.files['documento']
                    # Si el archivo es válido.
                    if file and allowed_file(file.filename):
                        # Obtiene la extensión.
                        ext = file.filename.rsplit('.', 1)[1].lower()
                        # Genera un nombre único con timestamp.
                        filename = secure_filename(f"solicitud_{dueno_id}_{int(time.time())}.{ext}")
                        # Crea la carpeta si no existe.
                        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                        # Guarda el archivo en la carpeta de subidas.
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        # Guarda la ruta relativa.
                        documento_path = f"uploads/perfiles/{filename}"

                # Crea una solicitud de dueño con estado 'pendiente'.
                cursor.execute("""
                    INSERT INTO solicitudes_dueno (dueno_id, nombre_local, ubicacion, descripcion, documento_path, estado_solicitud)
                    VALUES (%s, %s, %s, %s, %s, 'pendiente')
                """, (dueno_id, nombre_local, ubicacion, descripcion, documento_path))
                mysql.connection.commit()
                flash('Solicitud enviada. Espera la aprobación del administrador.', 'info')
                cursor.close()
                return redirect('/login')

            # ======= CASO: EMPLEADO =======
            elif tipo == 'empleado':
                # Obtiene datos específicos del empleado.
                codigo_local = request.form.get('codigo_local')
                puesto = request.form.get('puesto', '')
                mensaje = request.form.get('mensaje', '')

                # Valida que se haya ingresado el código del local.
                if not codigo_local:
                    flash('Debes ingresar el código del local.', 'danger')
                    return render_template('registro.html')

                # Busca el local por su código.
                cursor.execute("SELECT id FROM locales WHERE codigo = %s", (codigo_local,))
                local = cursor.fetchone()
                if not local:
                    flash('El código de local ingresado no es válido. Verifica e inténtalo de nuevo.', 'danger')
                    return render_template('registro.html')

                local_id = local[0]

                # Crea el usuario cliente (base para el empleado).
                cursor.execute("""
                    INSERT INTO usuarios (nombre, correo, password, fecha_nacimiento, telefono, direccion, documento_identidad, estado)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'activo')
                """, (nombre, correo, generate_password_hash(password), fecha, telefono, direccion, documento_identidad))
                mysql.connection.commit()
                usuario_id = cursor.lastrowid

                # Manejo del documento (opcional).
                documento_path = None
                if 'documento' in request.files:
                    file = request.files['documento']
                    if file and allowed_file(file.filename):
                        ext = file.filename.rsplit('.', 1)[1].lower()
                        filename = secure_filename(f"empleado_{usuario_id}_{int(time.time())}.{ext}")
                        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        documento_path = f"uploads/perfiles/{filename}"

                # Crea la solicitud de empleado con estado 'pendiente'.
                cursor.execute("""
                    INSERT INTO solicitudes_empleado (usuario_id, local_id, puesto, documento_path, mensaje, estado_solicitud)
                    VALUES (%s, %s, %s, %s, %s, 'pendiente')
                """, (usuario_id, local_id, puesto, documento_path, mensaje))
                mysql.connection.commit()
                flash('Solicitud enviada. El dueño del local la revisará y te notificará.', 'info')
                cursor.close()
                return redirect('/login')

            else:
                # Si tipo no es válido.
                flash('Tipo de cuenta no válido.', 'danger')
                return render_template('registro.html')

        except MySQLdb.IntegrityError as e:
            # Error de integridad (correo duplicado, etc.)
            mysql.connection.rollback()   # Deshace la transacción.
            if e.args[0] == 1062:
                # Código 1062 = entrada duplicada (correo ya registrado).
                flash('El correo electrónico ya está registrado. Por favor, usa otro o inicia sesión.', 'danger')
            else:
                flash('Error de integridad en la base de datos. Intenta de nuevo.', 'danger')
            return render_template('registro.html')

        except Exception as e:
            # Cualquier otra excepción.
            mysql.connection.rollback()
            flash(f'Ocurrió un error inesperado: {str(e)}', 'danger')
            return render_template('registro.html')

        finally:
            cursor.close()   # Asegura que el cursor se cierre.

    # Si es GET, muestra el formulario de registro.
    return render_template('registro.html')

# ========================================================================
# RUTA: '/logout'
# ========================================================================
# DESCRIPCIÓN: CIERRA LA SESIÓN DEL USUARIO Y REDIRIGE AL LOGIN.
# ========================================================================

@app.route('/logout')
def logout():
    # Elimina todos los datos de la sesión del usuario.
    session.clear()
    # Mensaje informativo.
    flash('Sesión cerrada correctamente.', 'info')
    # Redirige a la página de login.
    return redirect('/login')

# ========================================================================
# RUTA: '/perfil'
# ========================================================================
# DESCRIPCIÓN: MUESTRA EL PERFIL DEL USUARIO AUTENTICADO.
# OBTIENE LOS DATOS SEGÚN EL TIPO DE TABLA (cliente, dueno, empleado, admin).
# ========================================================================

@app.route('/perfil')
@login_required
# El decorador login_required exige que el usuario esté autenticado.
def perfil():
    # Obtiene el tipo de tabla y el ID del usuario desde la sesión.
    tipo = session['tipo_tabla']
    usuario_id = session['usuario_id']

    # Crea un cursor.
    cursor = mysql.connection.cursor()

    # ======= CASO: CLIENTE =======
    if tipo == 'cliente':
        # Consulta para obtener datos del cliente.
        cursor.execute("SELECT id, nombre, correo, telefono, direccion, foto_perfil, documento_identidad FROM usuarios WHERE id=%s", (usuario_id,))
        usuario = cursor.fetchone()
        rol_nombre = "Cliente"
        documentos = None
        user_data = None
        if usuario:
            # Construye el diccionario de datos del usuario.
            user_data = {
                'id': usuario[0],
                'nombre': usuario[1],
                'correo': usuario[2],
                'telefono': usuario[3],
                'direccion': usuario[4],
                'foto_perfil': usuario[5],
                'documento_identidad': usuario[6],
                'rol': rol_nombre,
                'tipo_tabla': tipo,
                'documentos': documentos,
                'imagen_url': f"/imagen/usuario/{usuario_id}" if tiene_imagen('usuario', usuario_id) else None
            }

    # ======= CASO: DUEÑO =======
    elif tipo == 'dueno':
        # Consulta para obtener datos del dueño.
        cursor.execute("SELECT id, nombre, correo, telefono, documento_identidad, foto_perfil, direccion FROM duenos WHERE id=%s", (usuario_id,))
        usuario = cursor.fetchone()
        rol_nombre = "Dueño de negocio"
        documento_path = None
        if usuario:
            # Obtiene el documento de la solicitud aprobada más reciente.
            cursor.execute("SELECT documento_path FROM solicitudes_dueno WHERE dueno_id=%s AND estado_solicitud='aprobado' ORDER BY fecha_solicitud DESC LIMIT 1", (usuario_id,))
            solicitud = cursor.fetchone()
            documento_path = solicitud[0] if solicitud else None
            documentos = {'identidad': usuario[4], 'solicitud': documento_path}
            user_data = {
                'id': usuario[0],
                'nombre': usuario[1],
                'correo': usuario[2],
                'telefono': usuario[3],
                'documento_identidad': usuario[4],
                'foto_perfil': usuario[5],
                'direccion': usuario[6],
                'rol': rol_nombre,
                'tipo_tabla': tipo,
                'documentos': documentos,
                'imagen_url': f"/imagen/usuario/{usuario_id}" if tiene_imagen('usuario', usuario_id) else None
            }

    # ======= CASO: EMPLEADO =======
    elif tipo == 'empleado':
        # Consulta para obtener datos del empleado (incluye el local).
        cursor.execute("""
            SELECT e.id, e.nombre, e.correo, e.telefono, e.puesto, e.fecha_contratacion, e.foto_perfil, l.nombre as local_nombre, e.rol
            FROM empleados e
            JOIN locales l ON e.local_id = l.id
            WHERE e.id=%s
        """, (usuario_id,))
        usuario = cursor.fetchone()
        rol_nombre = "Empleado"
        documentos = None
        if usuario:
            user_data = {
                'id': usuario[0],
                'nombre': usuario[1],
                'correo': usuario[2],
                'telefono': usuario[3],
                'puesto': usuario[4],
                'fecha_contratacion': usuario[5],
                'foto_perfil': usuario[6],
                'local_nombre': usuario[7],
                'rol_empresa': usuario[8],
                'rol': rol_nombre,
                'tipo_tabla': tipo,
                'documentos': documentos,
                'imagen_url': f"/imagen/usuario/{usuario_id}" if tiene_imagen('usuario', usuario_id) else None
            }

    # ======= CASO: ADMINISTRADOR =======
    elif tipo == 'admin':
        # Consulta para obtener datos del administrador.
        cursor.execute("SELECT id, nombre, correo, telefono, foto_perfil FROM administradores WHERE id=%s", (usuario_id,))
        usuario = cursor.fetchone()
        rol_nombre = "Administrador del sistema"
        documentos = None
        if usuario:
            user_data = {
                'id': usuario[0],
                'nombre': usuario[1],
                'correo': usuario[2],
                'telefono': usuario[3],
                'foto_perfil': usuario[4],
                'rol': rol_nombre,
                'tipo_tabla': tipo,
                'documentos': documentos,
                'imagen_url': f"/imagen/usuario/{usuario_id}" if tiene_imagen('usuario', usuario_id) else None
            }

    else:
        # Si el tipo no es reconocido.
        cursor.close()
        flash('Tipo de usuario no válido.', 'danger')
        return redirect('/inicio')

    cursor.close()

    # Si no se encontraron datos del usuario.
    if not user_data:
        flash('Usuario no encontrado.', 'danger')
        return redirect('/inicio')

    # Si tiene imagen en MongoDB, actualiza la URL.
    if tiene_imagen('usuario', usuario_id):
        user_data['imagen_url'] = f"/imagen/usuario/{usuario_id}"
    else:
        user_data['imagen_url'] = None

    # ======= OBTENER FAVORITOS (CON TIPO_USUARIO) =======
    # Se obtiene el tipo de usuario desde la sesión para filtrar los favoritos
    # de acuerdo al rol, permitiendo que cada rol tenga sus propios favoritos.
    cursor = mysql.connection.cursor()
    # Consulta para obtener los productos favoritos del usuario, filtrando por tipo_usuario.
    cursor.execute("""
        SELECT p.id, p.nombre, p.precio, p.stock, l.nombre as local_nombre, l.codigo as local_codigo
        FROM favoritos f
        JOIN productos p ON f.producto_id = p.id
        JOIN locales l ON p.local_id = l.id
        WHERE f.usuario_id = %s AND f.tipo_usuario = %s
    """, (usuario_id, session['tipo_tabla']))
    # Se pasa el ID del usuario y el tipo de tabla (cliente, dueno, empleado, admin)
    # para obtener solo los favoritos correspondientes a ese rol.

    favoritos_rows = cursor.fetchall()
    cursor.close()

    # Lista para almacenar favoritos procesados.
    favoritos_list = []
    for row in favoritos_rows:
        # Por cada fila, se construye un diccionario con los datos del producto favorito.
        favoritos_list.append({
            'id': row[0],                       # ID del producto.
            'nombre': row[1],                   # Nombre del producto.
            'precio': float(row[2]),            # Precio (convertido a float).
            'stock': row[3],                    # Stock disponible.
            'local_nombre': row[4],             # Nombre del local.
            'local_codigo': row[5],             # Código del local.
            'imagen_url': f"/imagen/producto/{row[0]}" if tiene_imagen('producto', row[0]) else None
            # URL de la imagen del producto si existe.
        })

    # Renderiza la plantilla de perfil con los datos.
    return render_template('perfil.html', usuario=user_data, favoritos=favoritos_list)

# ========================================================================
# RUTA: '/mis-pedidos'
# ========================================================================
# DESCRIPCIÓN: MUESTRA LA LISTA DE PEDIDOS DEL USUARIO AUTENTICADO.
# ========================================================================

@app.route('/mis-pedidos')
@login_required
def mis_pedidos():
    # Obtiene el ID del usuario desde la sesión.
    usuario_id = session['usuario_id']

    cursor = mysql.connection.cursor()
    # Consulta todos los pedidos del usuario con detalles del local.
    cursor.execute("""
        SELECT p.id, p.codigo, p.total, p.fecha, p.estado,
            l.nombre as local_nombre, p.fecha_recogida, p.hora_recogida
        FROM pedidos p
        JOIN locales l ON p.local_id = l.id
        WHERE p.usuario_id = %s
        ORDER BY p.fecha DESC
    """, (usuario_id,))
    pedidos = cursor.fetchall()
    cursor.close()

    # Lista para almacenar pedidos procesados.
    pedidos_list = []
    for row in pedidos:
        pedidos_list.append({
            'id': row[0],
            'codigo': row[1],
            'total': float(row[2]),
            'fecha': row[3],
            'estado': row[4],
            'local_nombre': row[5],
            'fecha_recogida': row[6],
            'hora_recogida': row[7]
        })

    # Renderiza la vista de mis pedidos.
    return render_template('mis_pedidos.html', pedidos=pedidos_list)

# ========================================================================
# RUTA: '/subir_foto' (SISTEMA DE ARCHIVOS - OBSOLETO, SE USA MONGODB)
# ========================================================================
# DESCRIPCIÓN: ACTUALIZA LA FOTO DE PERFIL DEL USUARIO EN EL SISTEMA
# DE ARCHIVOS. ESTA RUTA SE MANTIENE POR COMPATIBILIDAD, PERO LA
# FUNCIONALIDAD PRINCIPAL USA MONGODB A TRAVÉS DE '/perfil/imagen'.
# ========================================================================

@app.route('/subir_foto', methods=['POST'])
@login_required
def subir_foto():
    # Obtiene el tipo de usuario y su ID desde la sesión.
    tipo = session['tipo_tabla']
    usuario_id = session['usuario_id']

    # Obtiene el archivo del formulario.
    file = request.files.get('foto')

    # Si el archivo es válido.
    if file and allowed_file(file.filename):
        # Obtiene la extensión.
        ext = file.filename.rsplit('.', 1)[1].lower()
        # Genera un nombre único con timestamp.
        filename = secure_filename(f"{tipo}_{usuario_id}_{int(time.time())}.{ext}")
        # Crea la carpeta si no existe.
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        # Ruta completa del archivo.
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        # Guarda el archivo.
        file.save(filepath)

        # Ruta relativa para la base de datos.
        db_path = f"uploads/perfiles/{filename}"

        # Crea un cursor.
        cursor = mysql.connection.cursor()

        # Actualiza la foto_perfil en la tabla correspondiente.
        if tipo == 'cliente':
            cursor.execute("UPDATE usuarios SET foto_perfil=%s WHERE id=%s", (db_path, usuario_id))
        elif tipo == 'dueno':
            cursor.execute("UPDATE duenos SET foto_perfil=%s WHERE id=%s", (db_path, usuario_id))
        elif tipo == 'empleado':
            cursor.execute("UPDATE empleados SET foto_perfil=%s WHERE id=%s", (db_path, usuario_id))
        elif tipo == 'admin':
            cursor.execute("UPDATE administradores SET foto_perfil=%s WHERE id=%s", (db_path, usuario_id))
        else:
            cursor.close()
            flash('Tipo de usuario no válido.', 'danger')
            return redirect('/perfil')

        # Confirma la actualización.
        mysql.connection.commit()
        cursor.close()
        flash('Foto de perfil actualizada.', 'success')

    else:
        flash('Archivo no válido. Formatos permitidos: JPG, PNG, GIF.', 'danger')

    # Redirige a la página de perfil.
    return redirect('/perfil')

# ========================================================================
# RUTAS API PÚBLICAS
# ========================================================================

# ========================================================================
# RUTA: '/api/productos'
# ========================================================================
# DESCRIPCIÓN: DEVUELVE UNA LISTA DE PRODUCTOS DISPONIBLES EN FORMATO JSON.
# SOLO PRODUCTOS CON STOCK > 0, LIMITADO A 30 REGISTROS.
# ========================================================================

@app.route('/api/productos')
def api_productos():
    cursor = mysql.connection.cursor()
    # Consulta los últimos 30 productos con stock mayor a 0.
    cursor.execute("""
        SELECT p.id, p.nombre, p.precio, p.stock, l.nombre as local_nombre
        FROM productos p
        JOIN locales l ON p.local_id = l.id
        WHERE p.stock > 0
        ORDER BY p.id DESC
        LIMIT 30
    """)

    # Lista para productos.
    productos = []
    for row in cursor.fetchall():
        producto_id = row[0]
        productos.append({
            'id': producto_id,
            'nombre': row[1],
            'precio': float(row[2]),
            'stock': row[3],
            'local_nombre': row[4],
            'imagen_url': f"/imagen/producto/{producto_id}" if tiene_imagen('producto', producto_id) else None
        })

    cursor.close()
    # Retorna en formato JSON.
    return jsonify(productos)

# ========================================================================
# RUTA: '/api/producto-stock/<int:id>'
# ========================================================================
# DESCRIPCIÓN: DEVUELVE EL STOCK DE UN PRODUCTO ESPECÍFICO EN JSON.
# ========================================================================

@app.route('/api/producto-stock/<int:id>')
def api_producto_stock(id):
    cursor = mysql.connection.cursor()
    # Consulta el stock del producto.
    cursor.execute("SELECT stock FROM productos WHERE id=%s", (id,))
    row = cursor.fetchone()
    cursor.close()
    # Retorna el stock o 0 si no existe.
    return jsonify({'stock': row[0] if row else 0})

# ========================================================================
# RUTA: '/api/locales'
# ========================================================================
# DESCRIPCIÓN: DEVUELVE LA LISTA DE TODOS LOS LOCALES EN FORMATO JSON.
# ========================================================================

@app.route('/api/locales')
def api_locales():
    cursor = mysql.connection.cursor()
    # Consulta todos los locales.
    cursor.execute("SELECT codigo, nombre, categoria FROM locales ORDER BY categoria, nombre")
    # Construye la lista de diccionarios.
    locales = [{'codigo': row[0], 'nombre': row[1], 'categoria': row[2]} for row in cursor.fetchall()]
    cursor.close()
    return jsonify(locales)

# ========================================================================
# RUTA: '/api/locales/categoria/<categoria>'
# ========================================================================
# DESCRIPCIÓN: DEVUELVE LOS LOCALES DE UNA CATEGORÍA ESPECÍFICA EN JSON.
# ========================================================================

@app.route('/api/locales/categoria/<categoria>')
def api_locales_por_categoria(categoria):
    cursor = mysql.connection.cursor()
    # Filtra locales por categoría.
    cursor.execute("SELECT codigo, nombre FROM locales WHERE categoria = %s ORDER BY nombre", (categoria,))
    locales = [{'codigo': row[0], 'nombre': row[1]} for row in cursor.fetchall()]
    cursor.close()
    return jsonify(locales)

# ========================================================================
# RUTAS API DEL CARRITO
# ========================================================================

# ========================================================================
# RUTA: '/api/carrito' (GET)
# ========================================================================
# DESCRIPCIÓN: DEVUELVE EL CARRITO DEL USUARIO AUTENTICADO EN JSON.
# ========================================================================

@app.route('/api/carrito')
def api_carrito():
    # Si no está autenticado, retorna error 401.
    if 'usuario_id' not in session:
        return jsonify({'error': 'login requerido'}), 401

    # Obtiene items y total del carrito.
    items, total = obtener_carrito_db(session['usuario_id'])
    # Retorna en JSON.
    return jsonify({'items': items, 'total': total})

# ========================================================================
# RUTA: '/api/carrito/agregar' (POST)
# ========================================================================
# DESCRIPCIÓN: AGREGA UN PRODUCTO AL CARRITO DEL USUARIO.
# DESCUENTA EL STOCK DEL PRODUCTO DE FORMA ATÓMICA USANDO TRANSACCIONES.
# ========================================================================

@app.route('/api/carrito/agregar', methods=['POST'])
@login_required
def api_agregar_carrito():
    # Obtiene los datos JSON de la solicitud.
    data = request.get_json()
    # ID del producto.
    producto_id = data.get('id')
    # Cantidad a agregar (por defecto 1).
    cantidad = data.get('cantidad', 1)
    # ID del usuario desde la sesión.
    usuario_id = session['usuario_id']

    cursor = mysql.connection.cursor()

    try:
        # Inicia una transacción.
        cursor.execute("START TRANSACTION")

        # Bloquea la fila del producto para lectura/actualización (FOR UPDATE).
        cursor.execute("SELECT stock FROM productos WHERE id = %s FOR UPDATE", (producto_id,))
        row = cursor.fetchone()
        # Si el producto no existe.
        if not row:
            return jsonify({'error': 'Producto no encontrado'}), 404

        # Stock actual del producto.
        stock_actual = row[0]

        # Verifica si el producto ya está en el carrito.
        cursor.execute("SELECT cantidad FROM carrito WHERE usuario_id = %s AND producto_id = %s", (usuario_id, producto_id))
        existing = cursor.fetchone()
        # Cantidad actual en carrito o 0.
        cantidad_actual = existing[0] if existing else 0

        # Cantidad total después de agregar.
        nueva_cantidad_total = cantidad_actual + cantidad

        # Si no hay suficiente stock.
        if stock_actual < cantidad:
            return jsonify({'error': f'Stock insuficiente. Disponible: {stock_actual}'}), 400

        # Si ya existe en el carrito, actualiza la cantidad.
        if existing:
            cursor.execute("UPDATE carrito SET cantidad = %s WHERE usuario_id = %s AND producto_id = %s",
                        (nueva_cantidad_total, usuario_id, producto_id))
        else:
            # Si no existe, inserta.
            cursor.execute("INSERT INTO carrito (usuario_id, producto_id, cantidad) VALUES (%s, %s, %s)",
                        (usuario_id, producto_id, cantidad))

        # Calcula el nuevo stock.
        nuevo_stock = stock_actual - cantidad
        # Actualiza el stock del producto.
        cursor.execute("UPDATE productos SET stock = %s WHERE id = %s", (nuevo_stock, producto_id))

        # Confirma la transacción.
        cursor.execute("COMMIT")

        # Cuenta el total de items en carrito.
        cursor.execute("SELECT SUM(cantidad) FROM carrito WHERE usuario_id = %s", (usuario_id,))
        total_items = cursor.fetchone()[0] or 0

        cursor.close()
        return jsonify({'success': True, 'total_items': total_items})

    except Exception as e:
        # Si hay error, deshace la transacción.
        cursor.execute("ROLLBACK")
        cursor.close()
        return jsonify({'error': str(e)}), 500

# ========================================================================
# RUTA: '/api/carrito/actualizar' (POST)
# ========================================================================
# DESCRIPCIÓN: ACTUALIZA LA CANTIDAD DE UN PRODUCTO EN EL CARRITO.
# SI LA NUEVA CANTIDAD ES 0, ELIMINA EL PRODUCTO DEL CARRITO Y
# DEVUELVE EL STOCK AL PRODUCTO.
# ========================================================================

@app.route('/api/carrito/actualizar', methods=['POST'])
@login_required
def api_actualizar_carrito():
    # Obtiene los datos JSON.
    data = request.get_json()
    producto_id = data.get('id')
    nueva_cantidad = data.get('cantidad')
    usuario_id = session['usuario_id']

    cursor = mysql.connection.cursor()
    try:
        # Inicia transacción.
        cursor.execute("START TRANSACTION")

        # Bloquea la fila del carrito para actualización.
        cursor.execute("SELECT cantidad FROM carrito WHERE usuario_id = %s AND producto_id = %s FOR UPDATE", (usuario_id, producto_id))
        row = cursor.fetchone()
        # Si no está en carrito.
        if not row:
            return jsonify({'error': 'Producto no encontrado en carrito'}), 404

        # Cantidad actual en carrito.
        cantidad_actual = row[0]

        # Bloquea la fila del producto.
        cursor.execute("SELECT stock FROM productos WHERE id = %s FOR UPDATE", (producto_id,))
        stock_actual = cursor.fetchone()[0]

        # Si la nueva cantidad es 0 o negativa, elimina del carrito.
        if nueva_cantidad <= 0:
            # Devuelve todo el stock.
            nuevo_stock = stock_actual + cantidad_actual
            cursor.execute("DELETE FROM carrito WHERE usuario_id = %s AND producto_id = %s", (usuario_id, producto_id))
            cursor.execute("UPDATE productos SET stock = %s WHERE id = %s", (nuevo_stock, producto_id))

        # Si aumenta la cantidad.
        elif nueva_cantidad > cantidad_actual:
            diferencia = nueva_cantidad - cantidad_actual
            # Verifica stock suficiente.
            if stock_actual < diferencia:
                raise Exception(f'Stock insuficiente. Disponible: {stock_actual}')
            nuevo_stock = stock_actual - diferencia
            cursor.execute("UPDATE carrito SET cantidad = %s WHERE usuario_id = %s AND producto_id = %s",
                        (nueva_cantidad, usuario_id, producto_id))
            cursor.execute("UPDATE productos SET stock = %s WHERE id = %s", (nuevo_stock, producto_id))

        # Si disminuye la cantidad.
        elif nueva_cantidad < cantidad_actual:
            diferencia = cantidad_actual - nueva_cantidad
            # Devuelve la diferencia al stock.
            nuevo_stock = stock_actual + diferencia
            cursor.execute("UPDATE carrito SET cantidad = %s WHERE usuario_id = %s AND producto_id = %s",
                        (nueva_cantidad, usuario_id, producto_id))
            cursor.execute("UPDATE productos SET stock = %s WHERE id = %s", (nuevo_stock, producto_id))

        # Si nueva_cantidad == cantidad_actual, no se hace nada.

        # Confirma la transacción.
        cursor.execute("COMMIT")
        cursor.close()
        return jsonify({'success': True})

    except Exception as e:
        # Si hay error, deshace la transacción.
        cursor.execute("ROLLBACK")
        cursor.close()
        return jsonify({'error': str(e)}), 500

# ========================================================================
# RUTA: '/carrito'
# ========================================================================
# DESCRIPCIÓN: MUESTRA LA VISTA DEL CARRITO DEL USUARIO.
# ========================================================================

@app.route('/carrito')
@login_required
def ver_carrito():
    # Obtiene los items y el total del carrito.
    items, total = obtener_carrito_db(session['usuario_id'])
    # Renderiza la plantilla del carrito.
    return render_template('carrito.html', items=items, total=total)

# ========================================================================
# RUTAS DE CHECKOUT (FINALIZACIÓN DE COMPRA)
# ========================================================================

# ========================================================================
# RUTA: '/checkout' (GET)
# ========================================================================
# DESCRIPCIÓN: MUESTRA LA VISTA DE CHECKOUT CON EL CARRITO AGRUPADO POR LOCAL.
# ========================================================================

@app.route('/checkout', methods=['GET'])
@login_required
def checkout_get():
    usuario_id = session['usuario_id']
    # Agrupa el carrito por local.
    _, grupos = agrupar_carrito(usuario_id)

    # Si no hay grupos (carrito vacío).
    if not grupos:
        flash('El carrito está vacío.', 'warning')
        return redirect('/carrito')

    # Indica si todos los productos pertenecen a un solo local.
    single_local = len(grupos) == 1

    # Lista de locales para el selector si hay varios locales.
    locales = []
    if single_local:
        local_id = grupos[0]['local_id']
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, nombre, codigo FROM locales WHERE id=%s", (local_id,))
        locales = [{'id': row[0], 'nombre': row[1], 'codigo': row[2]} for row in cursor.fetchall()]
        cursor.close()

    # Renderiza la plantilla de checkout.
    return render_template('checkout.html',
                        error=None,
                        single_local=single_local,
                        grupos=grupos,
                        locales=locales)

# ========================================================================
# RUTA: '/checkout' (POST)
# ========================================================================
# DESCRIPCIÓN: PROCESA LA CREACIÓN DE PEDIDOS. PUEDE RECIBIR JSON
# (MÚLTIPLES LOCALES) O FORMULARIO TRADICIONAL (UN SOLO LOCAL).
# ========================================================================

@app.route('/checkout', methods=['POST'])
@login_required
def checkout_post():
    usuario_id = session['usuario_id']

    # ======= SOLICITUD JSON (MÚLTIPLES LOCALES) =======
    if request.is_json:
        data = request.get_json()
        # Lista de pedidos por local.
        pedidos_data = data.get('pedidos', [])

        if not pedidos_data:
            return jsonify({'error': 'No se enviaron pedidos'}), 400

        # Obtiene grupos actuales del carrito.
        _, grupos = agrupar_carrito(usuario_id)
        if not grupos:
            return jsonify({'error': 'Carrito vacío'}), 400

        # Lista para pedidos creados.
        pedidos_creados = []
        cursor = mysql.connection.cursor()

        try:
            # Itera sobre cada pedido (uno por local).
            for pedido in pedidos_data:
                local_id = pedido['local_id']
                fecha_recogida = pedido.get('fecha_recogida')
                hora_recogida = pedido.get('hora_recogida')

                # Busca el grupo correspondiente.
                grupo = next((g for g in grupos if g['local_id'] == local_id), None)
                if not grupo:
                    continue

                total_grupo = grupo['subtotal_local']
                # Genera código único.
                codigo = generar_codigo_pedido()

                # Inserta el pedido.
                cursor.execute("""
                    INSERT INTO pedidos (codigo, usuario_id, total, estado, fecha_recogida, hora_recogida, local_id)
                    VALUES (%s, %s, %s, 'pendiente', %s, %s, %s)
                """, (codigo, usuario_id, total_grupo, fecha_recogida, hora_recogida, local_id))
                pedido_id = cursor.lastrowid

                # Inserta cada detalle del pedido.
                for producto in grupo['productos']:
                    cursor.execute("""
                        INSERT INTO detalle_pedido (pedido_id, producto_id, cantidad, precio_unitario)
                        VALUES (%s, %s, %s, %s)
                    """, (pedido_id, producto['id'], producto['cantidad'], producto['precio']))

                # Agrega a la lista de pedidos creados.
                pedidos_creados.append({
                    'codigo': codigo,
                    'local_nombre': grupo['local_nombre'],
                    'total': total_grupo
                })

            # Vacía el carrito del usuario.
            cursor.execute("DELETE FROM carrito WHERE usuario_id=%s", (usuario_id,))
            # Confirma todas las inserciones.
            mysql.connection.commit()

        except Exception as e:
            # Si hay error, deshace la transacción.
            mysql.connection.rollback()
            return jsonify({'error': str(e)}), 500
        finally:
            cursor.close()

        # Retorna éxito con la lista de pedidos.
        return jsonify({'success': True, 'pedidos': pedidos_creados})

    # ======= FORMULARIO TRADICIONAL (UN SOLO LOCAL) =======
    else:
        local_id = request.form.get('local_id')
        fecha_recogida = request.form.get('fecha_recogida')
        hora_recogida = request.form.get('hora_recogida')

        if not local_id:
            flash('Debes seleccionar un local.', 'danger')
            return redirect('/checkout')

        # Obtiene grupos del carrito.
        _, grupos = agrupar_carrito(usuario_id)

        # Verifica que haya exactamente un grupo (un solo local).
        if not grupos or len(grupos) != 1:
            flash('El carrito no está listo para un solo pedido.', 'danger')
            return redirect('/carrito')

        grupo = grupos[0]
        total = grupo['subtotal_local']
        codigo = generar_codigo_pedido()

        cursor = mysql.connection.cursor()
        try:
            # Crea el pedido.
            cursor.execute("""
                INSERT INTO pedidos (codigo, usuario_id, total, estado, fecha_recogida, hora_recogida, local_id)
                VALUES (%s, %s, %s, 'pendiente', %s, %s, %s)
            """, (codigo, usuario_id, total, fecha_recogida, hora_recogida, local_id))
            pedido_id = cursor.lastrowid

            # Inserta los detalles del pedido.
            for producto in grupo['productos']:
                cursor.execute("""
                    INSERT INTO detalle_pedido (pedido_id, producto_id, cantidad, precio_unitario)
                    VALUES (%s, %s, %s, %s)
                """, (pedido_id, producto['id'], producto['cantidad'], producto['precio']))

            # Vacía el carrito.
            cursor.execute("DELETE FROM carrito WHERE usuario_id=%s", (usuario_id,))
            mysql.connection.commit()
            flash('Pedido creado correctamente.', 'success')

        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error al crear pedido: {str(e)}', 'danger')
            return redirect('/checkout')
        finally:
            cursor.close()

        # Redirige a la página de confirmación.
        return redirect(f'/pedido/confirmacion/{pedido_id}')

# ========================================================================
# RUTA: '/pedido/confirmacion/<int:pedido_id>'
# ========================================================================
# DESCRIPCIÓN: MUESTRA LA CONFIRMACIÓN DE UN PEDIDO ÚNICO.
# ========================================================================

@app.route('/pedido/confirmacion/<int:pedido_id>')
@login_required
def confirmacion_pedido(pedido_id):
    cursor = mysql.connection.cursor()
    # Consulta el pedido del usuario.
    cursor.execute("""
        SELECT codigo, total, fecha, estado, fecha_recogida, hora_recogida, local_id
        FROM pedidos
        WHERE id=%s AND usuario_id=%s
    """, (pedido_id, session['usuario_id']))
    pedido = cursor.fetchone()

    # Si no se encuentra el pedido.
    if not pedido:
        flash('Pedido no encontrado.', 'danger')
        return redirect('/mis-pedidos')

    # Obtiene el nombre del local.
    cursor.execute("SELECT nombre FROM locales WHERE id=%s", (pedido[6],))
    local = cursor.fetchone()
    cursor.close()

    # Renderiza la confirmación.
    return render_template('confirmacion.html', pedido={
        'codigo': pedido[0],
        'total': pedido[1],
        'fecha': pedido[2],
        'estado': pedido[3],
        'fecha_recogida': pedido[4],
        'hora_recogida': pedido[5],
        'local_nombre': local[0] if local else 'Desconocido'
    })

# ========================================================================
# RUTA: '/pedidos/confirmacion-multiple'
# ========================================================================
# DESCRIPCIÓN: MUESTRA LA CONFIRMACIÓN DE MÚLTIPLES PEDIDOS.
# ========================================================================

@app.route('/pedidos/confirmacion-multiple')
@login_required
def confirmacion_multiple():
    # Obtiene el parámetro 'pedidos' de la URL.
    pedidos_json = request.args.get('pedidos')
    if not pedidos_json:
        return redirect('/inicio')

    # Convierte de JSON a lista de diccionarios.
    pedidos = json.loads(pedidos_json)
    # Renderiza la plantilla de confirmación múltiple.
    return render_template('confirmacion_multiple.html', pedidos=pedidos)

# ========================================================================
# RUTAS DE ADMINISTRACIÓN: SOLICITUDES DE DUEÑO
# ========================================================================

# ========================================================================
# RUTA: '/admin/solicitud/<int:id>/aprobar'
# ========================================================================
# DESCRIPCIÓN: APRUEBA UNA SOLICITUD DE DUEÑO, ACTIVA AL DUEÑO Y CREA EL LOCAL.
# ========================================================================

@app.route('/admin/solicitud/<int:id>/aprobar')
@login_required
@rol_requerido(['admin'])
def aprobar_solicitud(id):
    cursor = mysql.connection.cursor()
    # Obtiene datos de la solicitud.
    cursor.execute("SELECT dueno_id, nombre_local, ubicacion, descripcion FROM solicitudes_dueno WHERE id=%s", (id,))
    sol = cursor.fetchone()

    if not sol:
        flash('Solicitud no encontrada.', 'danger')
        return redirect('/admin/solicitudes')

    dueno_id, nombre_local, ubicacion, descripcion_negocio = sol

    # Activa al dueño.
    cursor.execute("UPDATE duenos SET estado='activo' WHERE id=%s", (dueno_id,))

    # Genera código único para el local.
    codigo_local = nombre_local[:3].upper() + str(dueno_id)

    # Crea el local.
    cursor.execute("""
        INSERT INTO locales (codigo, nombre, descripcion, ubicacion, dueno_id, categoria, dias_stock)
        VALUES (%s, %s, %s, %s, %s, '', '')
    """, (codigo_local, nombre_local, descripcion_negocio, ubicacion, dueno_id))

    # Marca la solicitud como aprobada.
    cursor.execute("UPDATE solicitudes_dueno SET estado_solicitud='aprobado' WHERE id=%s", (id,))

    mysql.connection.commit()
    cursor.close()

    flash('Solicitud aprobada y local creado.', 'success')
    return redirect('/admin/solicitudes')

# ========================================================================
# RUTA: '/admin/solicitud/<int:id>/rechazar'
# ========================================================================
# DESCRIPCIÓN: RECHAZA UNA SOLICITUD DE DUEÑO Y DESACTIVA AL DUEÑO.
# ========================================================================

@app.route('/admin/solicitud/<int:id>/rechazar')
@login_required
@rol_requerido(['admin'])
def rechazar_solicitud(id):
    cursor = mysql.connection.cursor()
    # Actualiza el estado de la solicitud a 'rechazado'.
    cursor.execute("UPDATE solicitudes_dueno SET estado_solicitud='rechazado' WHERE id=%s", (id,))
    # Desactiva al dueño.
    cursor.execute("UPDATE duenos SET estado='inactivo' WHERE id=(SELECT dueno_id FROM solicitudes_dueno WHERE id=%s)", (id,))

    mysql.connection.commit()
    cursor.close()

    flash('Solicitud rechazada.', 'info')
    return redirect('/admin/solicitudes')

# ========================================================================
# RUTA: '/dueno/dashboard'
# ========================================================================
# DESCRIPCIÓN: PANEL DE CONTROL DEL DUEÑO. MUESTRA DATOS DE SU LOCAL.
# ========================================================================

@app.route('/dueno/dashboard')
@login_required
@rol_requerido(['dueno'])
def dashboard_dueno():
    cursor = mysql.connection.cursor()
    # Obtiene el local del dueño.
    cursor.execute("""
        SELECT id, codigo, nombre, descripcion, ubicacion, dueno_id, dias_stock, categoria
        FROM locales WHERE dueno_id = %s
    """, (session['usuario_id'],))
    local = cursor.fetchone()

    # Si no tiene local asignado.
    if not local:
        flash('No cuentas con un local asignado. Comunícate con un administrador.', 'danger')
        return redirect('/inicio')

    # Construye el diccionario de datos del local.
    local_data = {
        'id': local[0],
        'codigo': local[1],
        'nombre': local[2],
        'descripcion': local[3],
        'ubicacion': local[4],
        'usuario_id': local[5],
        'dias_stock': local[6],
        'categoria': local[7],
        'imagen_local_url': f"/imagen/local/{local[0]}" if tiene_imagen('local', local[0]) else None
    }
    cursor.close()

    return render_template('owner_dashboard.html', local=local_data)

# ========================================================================
# RUTA: '/dueno/multimedia'
# ========================================================================
# DESCRIPCIÓN: PANEL DE MULTIMEDIA PARA EL DUEÑO. PERMITE SUBIR Y
# ADMINISTRAR FOTOS, VIDEOS Y AUDIOS DEL LOCAL.
# ========================================================================

@app.route('/dueno/multimedia')
@login_required
@rol_requerido(['dueno'])
def multimedia_panel():
    cursor = mysql.connection.cursor()
    # Obtiene el local del dueño.
    cursor.execute("""
        SELECT id, codigo, nombre, descripcion, ubicacion, dueno_id, dias_stock, categoria
        FROM locales WHERE dueno_id = %s
    """, (session['usuario_id'],))
    local = cursor.fetchone()
    cursor.close()

    if not local:
        flash('No tienes un local asignado.', 'danger')
        return redirect('/inicio')

    local_data = {
        'id': local[0],
        'codigo': local[1],
        'nombre': local[2],
        'descripcion': local[3],
        'ubicacion': local[4],
        'dueno_id': local[5],
        'dias_stock': local[6],
        'categoria': local[7]
    }

    return render_template('multimedia_panel.html', local=local_data)

# ========================================================================
# RUTA: '/multimedia/<file_id>'
# ========================================================================
# DESCRIPCIÓN: SIRVE ARCHIVOS MULTIMEDIA DESDE GRIDFS (FOTOS, VIDEOS, AUDIOS).
# ========================================================================

@app.route('/multimedia/<file_id>')
def servir_multimedia(file_id):
    try:
        # Convierte el ID a ObjectId de MongoDB.
        obj_id = bson.ObjectId(file_id)
        # Obtiene el archivo de GridFS.
        grid_out = fs.get(obj_id)

        if not grid_out:
            abort(404)

        # Determina el tipo MIME.
        content_type = grid_out.content_type if grid_out.content_type else 'application/octet-stream'

        # Envía el archivo al cliente.
        return send_file(
            io.BytesIO(grid_out.read()),  # Lee el archivo en un buffer.
            mimetype=content_type,        # Tipo MIME.
            as_attachment=False,          # Lo muestra en el navegador.
            download_name=grid_out.filename
        )
    except Exception as e:
        abort(404)

# ========================================================================
# RUTAS API PARA DUEÑO: MULTIMEDIA
# ========================================================================

# ========================================================================
# RUTA: '/api/owner/multimedia' (GET)
# ========================================================================
# DESCRIPCIÓN: LISTA LOS ARCHIVOS MULTIMEDIA DE UN LOCAL.
# ========================================================================

@app.route('/api/owner/multimedia', methods=['GET'])
@login_required
@rol_requerido(['dueno'])
def owner_listar_multimedia():
    local_id = request.args.get('local_id')
    if not local_id:
        return jsonify({'error': 'Falta local_id'}), 400

    # Verifica que el local pertenezca al dueño.
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id FROM locales WHERE id=%s AND dueno_id=%s", (local_id, session['usuario_id']))
    if not cursor.fetchone():
        cursor.close()
        return jsonify({'error': 'No autorizado'}), 403
    cursor.close()

    # Obtiene la lista de archivos.
    files = listar_multimedia(int(local_id))
    return jsonify({'files': files})

# ========================================================================
# RUTA: '/api/owner/multimedia/upload' (POST)
# ========================================================================
# DESCRIPCIÓN: SUBE UN ARCHIVO MULTIMEDIA (FOTO, VIDEO, AUDIO) AL LOCAL.
# ========================================================================

@app.route('/api/owner/multimedia/upload', methods=['POST'])
@login_required
@rol_requerido(['dueno'])
def owner_subir_multimedia():
    local_id = request.form.get('local_id')
    if not local_id:
        return jsonify({'error': 'Falta local_id'}), 400

    try:
        local_id = int(local_id)
    except:
        return jsonify({'error': 'local_id inválido'}), 400

    # Verifica autorización.
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id FROM locales WHERE id=%s AND dueno_id=%s", (local_id, session['usuario_id']))
    if not cursor.fetchone():
        cursor.close()
        return jsonify({'error': 'No autorizado'}), 403
    cursor.close()

    if 'archivo' not in request.files:
        return jsonify({'error': 'No se envió archivo'}), 400

    file = request.files['archivo']
    if file.filename == '':
        return jsonify({'error': 'Archivo vacío'}), 400

    tipo = request.form.get('tipo', 'foto')
    descripcion = request.form.get('descripcion', '')

    if tipo not in ('foto', 'video', 'audio'):
        return jsonify({'error': 'Tipo inválido'}), 400

    # Guarda el archivo en GridFS.
    file_id = guardar_multimedia(local_id, file, tipo, descripcion)

    if file_id:
        return jsonify({'success': True, 'file_id': file_id})
    else:
        return jsonify({'error': 'Error al guardar el archivo'}), 500

# ========================================================================
# RUTA: '/api/owner/multimedia/<file_id>' (DELETE)
# ========================================================================
# DESCRIPCIÓN: ELIMINA UN ARCHIVO MULTIMEDIA DEL LOCAL.
# ========================================================================

@app.route('/api/owner/multimedia/<file_id>', methods=['DELETE'])
@login_required
@rol_requerido(['dueno'])
def owner_eliminar_multimedia(file_id):
    try:
        obj_id = bson.ObjectId(file_id)
        grid_out = fs.get(obj_id)

        if not grid_out:
            return jsonify({'error': 'Archivo no encontrado'}), 404

        # ID del local asociado.
        local_id = grid_out.id_coleccion if hasattr(grid_out, 'id_coleccion') else None
        if not local_id:
            return jsonify({'error': 'Archivo sin local asociado'}), 400

        # Verifica autorización.
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id FROM locales WHERE id=%s AND dueno_id=%s", (local_id, session['usuario_id']))
        if not cursor.fetchone():
            cursor.close()
            return jsonify({'error': 'No autorizado'}), 403
        cursor.close()

        # Elimina el archivo.
        if eliminar_multimedia(file_id):
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Error al eliminar'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ========================================================================
# RUTAS PARA SIRVIR IMÁGENES DESDE MONGODB
# ========================================================================

# ========================================================================
# RUTA: '/imagen/<coleccion>/<int:id>'
# ========================================================================
# DESCRIPCIÓN: SIRVE UNA IMAGEN ALMACENADA EN GRIDFS.
# ========================================================================

@app.route('/imagen/<coleccion>/<int:id>')
def servir_imagen(coleccion, id):
    # Obtiene el archivo de GridFS.
    grid_out = obtener_archivo(coleccion, id)
    if not grid_out:
        abort(404)

    # Envía la imagen al cliente.
    return send_file(
        io.BytesIO(grid_out.read()),
        mimetype=grid_out.content_type,
        as_attachment=False,
        download_name=grid_out.filename
    )

# ========================================================================
# RUTAS PARA ADMIN: SUBIR IMÁGENES
# ========================================================================

# ========================================================================
# RUTA: '/admin/producto/<int:producto_id>/imagen' (POST)
# ========================================================================
# DESCRIPCIÓN: ADMIN SUBE IMAGEN PARA UN PRODUCTO.
# ========================================================================

@app.route('/admin/producto/<int:producto_id>/imagen', methods=['POST'])
@login_required
@rol_requerido(['admin'])
def admin_subir_imagen_producto(producto_id):
    if 'imagen' not in request.files:
        flash('No se envió archivo.', 'danger')
        return redirect(url_for('admin_panel'))

    file = request.files['imagen']
    if file.filename == '':
        flash('Archivo vacío.', 'danger')
        return redirect(url_for('admin_panel'))

    guardar_archivo('producto', producto_id, file)
    flash('Imagen del producto actualizada.', 'success')
    return redirect(url_for('admin_panel'))

# ========================================================================
# RUTA: '/admin/local/<int:local_id>/imagen' (POST)
# ========================================================================
# DESCRIPCIÓN: ADMIN SUBE IMAGEN PARA UN LOCAL.
# ========================================================================

@app.route('/admin/local/<int:local_id>/imagen', methods=['POST'])
@login_required
@rol_requerido(['admin'])
def admin_subir_imagen_local(local_id):
    if 'imagen' not in request.files:
        flash('No se envió archivo.', 'danger')
        return redirect(url_for('admin_panel'))

    file = request.files['imagen']
    if file.filename == '':
        flash('Archivo vacío.', 'danger')
        return redirect(url_for('admin_panel'))

    guardar_archivo('local', local_id, file)
    flash('Imagen del local actualizada.', 'success')
    return redirect(url_for('admin_panel'))

# ========================================================================
# RUTAS PARA DUEÑO: SUBIR IMÁGENES
# ========================================================================

# ========================================================================
# RUTA: '/dueno/producto/<int:producto_id>/imagen' (POST)
# ========================================================================
# DESCRIPCIÓN: DUEÑO SUBE IMAGEN PARA UN PRODUCTO DE SU LOCAL.
# ========================================================================

@app.route('/dueno/producto/<int:producto_id>/imagen', methods=['POST'])
@login_required
@rol_requerido(['dueno'])
def dueno_subir_imagen_producto(producto_id):
    cursor = mysql.connection.cursor()
    # Verifica que el producto pertenezca a su local.
    cursor.execute("""
        SELECT p.id FROM productos p
        JOIN locales l ON p.local_id = l.id
        WHERE p.id = %s AND l.dueno_id = %s
    """, (producto_id, session['usuario_id']))

    if not cursor.fetchone():
        flash('No autorizado.', 'danger')
        cursor.close()
        return redirect('/dueno/dashboard')
    cursor.close()

    if 'imagen' not in request.files:
        flash('No se envió archivo.', 'danger')
        return redirect('/dueno/dashboard')

    file = request.files['imagen']
    if file.filename == '':
        flash('Archivo vacío.', 'danger')
        return redirect('/dueno/dashboard')

    guardar_archivo('producto', producto_id, file)
    flash('Imagen del producto actualizada.', 'success')
    return redirect('/dueno/dashboard')

# ========================================================================
# RUTA: '/dueno/local/imagen' (POST)
# ========================================================================
# DESCRIPCIÓN: DUEÑO SUBE IMAGEN PARA SU LOCAL.
# ========================================================================

@app.route('/dueno/local/imagen', methods=['POST'])
@login_required
@rol_requerido(['dueno'])
def dueno_subir_imagen_local():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id FROM locales WHERE dueno_id=%s", (session['usuario_id'],))
    local = cursor.fetchone()
    cursor.close()

    if not local:
        flash('No tienes un local asignado.', 'danger')
        return redirect('/dueno/dashboard')

    local_id = local[0]

    if 'imagen' not in request.files:
        flash('No se envió archivo.', 'danger')
        return redirect('/dueno/dashboard')

    file = request.files['imagen']
    if file.filename == '':
        flash('Archivo vacío.', 'danger')
        return redirect('/dueno/dashboard')

    guardar_archivo('local', local_id, file)
    flash('Imagen del local actualizada.', 'success')
    return redirect('/dueno/dashboard')

# ========================================================================
# RUTA: '/perfil/imagen' (POST)
# ========================================================================
# DESCRIPCIÓN: SUBE FOTO DE PERFIL USANDO MONGODB.
# ========================================================================

@app.route('/perfil/imagen', methods=['POST'])
@login_required
def subir_foto_perfil_mongo():
    if 'foto' not in request.files:
        return jsonify({'error': 'No se envió archivo'}), 400

    file = request.files['foto']
    if file.filename == '':
        return jsonify({'error': 'Archivo vacío'}), 400

    usuario_id = session['usuario_id']
    file_id = guardar_archivo('usuario', usuario_id, file)

    if file_id:
        return jsonify({'success': True, 'message': 'Foto actualizada', 'usuario_id': usuario_id})
    else:
        return jsonify({'error': 'Error al guardar'}), 500

# ========================================================================
# RUTAS API PARA DUEÑO (DASHBOARD)
# ========================================================================

# ========================================================================
# RUTA: '/dueno/producto/agregar' (POST)
# ========================================================================
# DESCRIPCIÓN: DUEÑO AGREGA UN PRODUCTO A SU LOCAL.
# ========================================================================

@app.route('/dueno/producto/agregar', methods=['POST'])
@login_required
@rol_requerido(['dueno'])
def dueno_agregar_producto():
    nombre = request.form.get('nombre')
    precio = request.form.get('precio')
    stock = request.form.get('stock')

    if not nombre or not precio or not stock:
        flash('Faltan datos obligatorios.', 'danger')
        return redirect('/dueno/dashboard')

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id FROM locales WHERE dueno_id=%s", (session['usuario_id'],))
    local = cursor.fetchone()

    if not local:
        flash('No tienes un local registrado.', 'danger')
        return redirect('/dueno/dashboard')

    local_id = local[0]

    # Inserta el producto.
    cursor.execute("INSERT INTO productos (nombre, precio, stock, local_id) VALUES (%s, %s, %s, %s)",
                (nombre, float(precio), int(stock), local_id))

    mysql.connection.commit()
    cursor.close()

    flash('Producto agregado correctamente.', 'success')
    return redirect('/dueno/dashboard')

# ========================================================================
# RUTA: '/api/owner/stats' (GET)
# ========================================================================
# DESCRIPCIÓN: DEVUELVE ESTADÍSTICAS DEL LOCAL DEL DUEÑO.
# ========================================================================

@app.route('/api/owner/stats')
@login_required
@rol_requerido(['dueno'])
def owner_stats():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id FROM locales WHERE dueno_id=%s", (session['usuario_id'],))
    local = cursor.fetchone()

    if not local:
        return jsonify({'error': 'Local no encontrado'}), 404

    local_id = local[0]

    # Total de productos.
    cursor.execute("SELECT COUNT(*) FROM productos WHERE local_id=%s", (local_id,))
    total_products = cursor.fetchone()[0]

    # Pedidos pendientes.
    cursor.execute("SELECT COUNT(*) FROM pedidos WHERE local_id=%s AND estado='pendiente'", (local_id,))
    pending_orders = cursor.fetchone()[0]

    # Ingresos totales (pedidos entregados).
    cursor.execute("SELECT SUM(total) FROM pedidos WHERE local_id=%s AND estado='entregado'", (local_id,))
    total_revenue = cursor.fetchone()[0] or 0

    # Productos con stock bajo (<= 5).
    cursor.execute("SELECT COUNT(*) FROM productos WHERE local_id=%s AND stock <= 5", (local_id,))
    low_stock = cursor.fetchone()[0]

    cursor.close()

    return jsonify({
        'total_products': total_products,
        'pending_orders': pending_orders,
        'total_revenue': float(total_revenue),
        'low_stock': low_stock
    })

# ========================================================================
# RUTA: '/api/owner/products' (GET)
# ========================================================================
# DESCRIPCIÓN: LISTA LOS PRODUCTOS DEL LOCAL DEL DUEÑO.
# ========================================================================

@app.route('/api/owner/products')
@login_required
@rol_requerido(['dueno'])
def owner_products():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id FROM locales WHERE dueno_id=%s", (session['usuario_id'],))
    local = cursor.fetchone()

    if not local:
        return jsonify([])

    local_id = local[0]

    cursor.execute("SELECT id, nombre, precio, stock FROM productos WHERE local_id=%s", (local_id,))
    productos = []
    for row in cursor.fetchall():
        producto_id = row[0]
        productos.append({
            'id': producto_id,
            'nombre': row[1],
            'precio': float(row[2]),
            'stock': row[3],
            'imagen_url': f"/imagen/producto/{producto_id}" if tiene_imagen('producto', producto_id) else None
        })

    cursor.close()
    return jsonify(productos)

# ========================================================================
# RUTA: '/api/owner/product/<int:id>' (PUT)
# ========================================================================
# DESCRIPCIÓN: ACTUALIZA UN PRODUCTO DEL LOCAL DEL DUEÑO.
# ========================================================================

@app.route('/api/owner/product/<int:id>', methods=['PUT'])
@login_required
@rol_requerido(['dueno'])
def owner_update_product(id):
    data = request.get_json()
    cursor = mysql.connection.cursor()
    # Verifica propiedad del producto.
    cursor.execute("""
        SELECT pr.local_id FROM productos pr
        JOIN locales l ON pr.local_id = l.id
        WHERE pr.id=%s AND l.dueno_id=%s
    """, (id, session['usuario_id']))

    if not cursor.fetchone():
        return jsonify({'error': 'No autorizado'}), 403

    # Actualiza el producto.
    cursor.execute("UPDATE productos SET nombre=%s, precio=%s, stock=%s WHERE id=%s",
                (data['nombre'], data['precio'], data['stock'], id))

    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True})

# ========================================================================
# RUTA: '/api/owner/product/<int:id>' (DELETE)
# ========================================================================
# DESCRIPCIÓN: ELIMINA UN PRODUCTO DEL LOCAL DEL DUEÑO.
# ========================================================================

@app.route('/api/owner/product/<int:id>', methods=['DELETE'])
@login_required
@rol_requerido(['dueno'])
def owner_delete_product(id):
    cursor = mysql.connection.cursor()
    # Verifica propiedad del producto.
    cursor.execute("""
        SELECT pr.local_id FROM productos pr
        JOIN locales l ON pr.local_id = l.id
        WHERE pr.id=%s AND l.dueno_id=%s
    """, (id, session['usuario_id']))

    if not cursor.fetchone():
        return jsonify({'error': 'No autorizado'}), 403

    # Elimina el producto.
    cursor.execute("DELETE FROM productos WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True})

# ========================================================================
# RUTA: '/api/owner/orders' (GET)
# ========================================================================
# DESCRIPCIÓN: LISTA LOS PEDIDOS DEL LOCAL DEL DUEÑO.
# ========================================================================

@app.route('/api/owner/orders')
@login_required
@rol_requerido(['dueno'])
def owner_orders():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id FROM locales WHERE dueno_id=%s", (session['usuario_id'],))
    local = cursor.fetchone()

    if not local:
        return jsonify([])

    local_id = local[0]

    cursor.execute("""
        SELECT p.id, p.codigo, u.nombre, p.total, p.estado
        FROM pedidos p
        JOIN usuarios u ON p.usuario_id = u.id
        WHERE p.local_id = %s
        ORDER BY p.id DESC
    """, (local_id,))

    pedidos = [{'id': row[0], 'codigo': row[1], 'cliente': row[2], 'total': float(row[3]), 'estado': row[4]} for row in cursor.fetchall()]
    cursor.close()
    return jsonify(pedidos)

# ========================================================================
# RUTA: '/api/owner/order/<int:id>/status' (POST)
# ========================================================================
# DESCRIPCIÓN: ACTUALIZA EL ESTADO DE UN PEDIDO DEL LOCAL DEL DUEÑO.
# ========================================================================

@app.route('/api/owner/order/<int:id>/status', methods=['POST'])
@login_required
@rol_requerido(['dueno'])
def owner_update_order_status(id):
    data = request.get_json()
    nuevo_estado = data.get('estado')

    if nuevo_estado not in ('pendiente', 'listo', 'entregado', 'cancelado'):
        return jsonify({'success': False, 'message': 'Estado inválido'}), 400

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT local_id FROM pedidos WHERE id=%s", (id,))
    pedido = cursor.fetchone()

    if not pedido:
        return jsonify({'error': 'Pedido no encontrado'}), 404

    # Verifica que el pedido pertenezca al local del dueño.
    cursor.execute("SELECT dueno_id FROM locales WHERE id=%s", (pedido[0],))
    dueno = cursor.fetchone()

    if not dueno or dueno[0] != session['usuario_id']:
        return jsonify({'error': 'No autorizado'}), 403

    # Actualiza el estado del pedido.
    cursor.execute("UPDATE pedidos SET estado=%s WHERE id=%s", (nuevo_estado, id))

    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True})

# ========================================================================
# RUTA: '/api/owner/local/update' (POST)
# ========================================================================
# DESCRIPCIÓN: ACTUALIZA CATEGORÍA Y DÍAS DE STOCK DEL LOCAL.
# ========================================================================

@app.route('/api/owner/local/update', methods=['POST'])
@login_required
@rol_requerido(['dueno'])
def owner_update_local():
    data = request.get_json()
    local_id = data.get('local_id')
    categoria = data.get('categoria', '')
    dias_stock = data.get('dias_stock', '')

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id FROM locales WHERE id=%s AND dueno_id=%s", (local_id, session['usuario_id']))
    if not cursor.fetchone():
        return jsonify({'error': 'No autorizado'}), 403

    cursor.execute("UPDATE locales SET categoria=%s, dias_stock=%s WHERE id=%s", (categoria, dias_stock, local_id))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True})

# ========================================================================
# RUTAS API PARA DUEÑO: EMPLEADOS
# ========================================================================

# ========================================================================
# RUTA: '/api/owner/empleados' (GET)
# ========================================================================
# DESCRIPCIÓN: LISTA LOS EMPLEADOS DEL LOCAL DEL DUEÑO.
# ========================================================================

@app.route('/api/owner/empleados', methods=['GET'])
@login_required
@rol_requerido(['dueno'])
def owner_empleados():
    local_id = request.args.get('local_id')
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id FROM locales WHERE id=%s AND dueno_id=%s", (local_id, session['usuario_id']))
    if not cursor.fetchone():
        return jsonify({'error': 'No autorizado'}), 403

    cursor.execute("""
        SELECT e.id, e.nombre, e.correo, e.puesto
        FROM empleados e
        WHERE e.local_id = %s
    """, (local_id,))

    empleados = [{'id': row[0], 'nombre': row[1], 'correo': row[2], 'puesto': row[3]} for row in cursor.fetchall()]
    cursor.close()
    return jsonify(empleados)

# ========================================================================
# RUTA: '/api/owner/empleados/agregar' (POST)
# ========================================================================
# DESCRIPCIÓN: AGREGA UN EMPLEADO AL LOCAL DEL DUEÑO.
# ========================================================================

@app.route('/api/owner/empleados/agregar', methods=['POST'])
@login_required
@rol_requerido(['dueno'])
def owner_add_empleado():
    data = request.get_json()
    local_id = data.get('local_id')
    correo = data.get('correo')
    puesto = data.get('puesto')

    if not local_id or not correo or not puesto:
        return jsonify({'error': 'Faltan datos'}), 400

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id FROM locales WHERE id=%s AND dueno_id=%s", (local_id, session['usuario_id']))
    if not cursor.fetchone():
        return jsonify({'error': 'No autorizado'}), 403

    # Verifica que no esté ya registrado como empleado en este local.
    cursor.execute("SELECT id FROM empleados WHERE correo=%s AND local_id=%s", (correo, local_id))
    if cursor.fetchone():
        return jsonify({'error': 'El empleado ya está registrado en este local'}), 400

    # Verifica que no sea dueño.
    cursor.execute("SELECT id FROM duenos WHERE correo=%s", (correo,))
    dueno = cursor.fetchone()
    if dueno:
        return jsonify({'error': 'Un dueño no puede ser empleado'}), 400

    # Busca si el correo existe en usuarios.
    cursor.execute("SELECT id, nombre FROM usuarios WHERE correo=%s", (correo,))
    cliente = cursor.fetchone()

    if cliente:
        # Si existe, usa sus datos.
        nombre_real = cliente[1]
        # Genera contraseña temporal.
        password_temp = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        cursor.execute("""
            INSERT INTO empleados (nombre, correo, password, local_id, puesto)
            VALUES (%s, %s, %s, %s, %s)
        """, (nombre_real, correo, generate_password_hash(password_temp), local_id, puesto))
        mysql.connection.commit()
        cursor.close()
        return jsonify({'success': True, 'message': 'Empleado agregado (se generó contraseña temporal)'})

    # Si no existe en usuarios, crea uno nuevo.
    nombre_temp = correo.split('@')[0]
    password_temp = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    cursor.execute("""
        INSERT INTO empleados (nombre, correo, password, local_id, puesto)
        VALUES (%s, %s, %s, %s, %s)
    """, (nombre_temp, correo, generate_password_hash(password_temp), local_id, puesto))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True, 'message': 'Empleado creado. Se ha generado una contraseña temporal.'})

# ========================================================================
# RUTA: '/api/owner/empleados/<int:id>' (DELETE)
# ========================================================================
# DESCRIPCIÓN: ELIMINA UN EMPLEADO DEL LOCAL DEL DUEÑO.
# ========================================================================

@app.route('/api/owner/empleados/<int:id>', methods=['DELETE'])
@login_required
@rol_requerido(['dueno'])
def owner_delete_empleado(id):
    cursor = mysql.connection.cursor()
    # Verifica que el empleado pertenezca al local del dueño.
    cursor.execute("""
        SELECT e.local_id FROM empleados e
        JOIN locales l ON e.local_id = l.id
        WHERE e.id = %s AND l.dueno_id = %s
    """, (id, session['usuario_id']))

    if not cursor.fetchone():
        return jsonify({'error': 'No autorizado'}), 403

    cursor.execute("DELETE FROM empleados WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True})

# ========================================================================
# RUTAS API PARA DUEÑO: SOLICITUDES DE EMPLEADO
# ========================================================================

# ========================================================================
# RUTA: '/api/owner/employee_requests' (GET)
# ========================================================================
# DESCRIPCIÓN: LISTA LAS SOLICITUDES DE EMPLEADO PENDIENTES PARA EL LOCAL.
# ========================================================================

@app.route('/api/owner/employee_requests')
@login_required
@rol_requerido(['dueno'])
def owner_employee_requests():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id FROM locales WHERE dueno_id = %s", (session['usuario_id'],))
    local = cursor.fetchone()

    if not local:
        return jsonify([])

    local_id = local[0]

    cursor.execute("""
        SELECT se.id, se.usuario_id, u.nombre, u.correo, se.puesto, se.mensaje, se.documento_path, se.fecha_solicitud
        FROM solicitudes_empleado se
        JOIN usuarios u ON se.usuario_id = u.id
        WHERE se.local_id = %s AND se.estado_solicitud = 'pendiente'
        ORDER BY se.fecha_solicitud DESC
    """, (local_id,))

    rows = cursor.fetchall()
    cursor.close()

    solicitudes = []
    for r in rows:
        solicitudes.append({
            'id': r[0],
            'usuario_id': r[1],
            'nombre': r[2],
            'correo': r[3],
            'puesto': r[4],
            'mensaje': r[5],
            'documento_path': r[6],
            'fecha': r[7].strftime('%Y-%m-%d %H:%M')
        })

    return jsonify(solicitudes)

# ========================================================================
# RUTA: '/api/owner/employee_request/<int:id>/approve' (POST)
# ========================================================================
# DESCRIPCIÓN: APRUEBA UNA SOLICITUD DE EMPLEADO Y CREA EL EMPLEADO.
# ========================================================================

@app.route('/api/owner/employee_request/<int:id>/approve', methods=['POST'])
@login_required
@rol_requerido(['dueno'])
def owner_approve_employee(id):
    cursor = mysql.connection.cursor()
    # Obtiene datos de la solicitud.
    cursor.execute("""
        SELECT se.usuario_id, se.local_id, se.puesto, u.nombre, u.correo, u.password, u.foto_perfil
        FROM solicitudes_empleado se
        JOIN usuarios u ON se.usuario_id = u.id
        JOIN locales l ON se.local_id = l.id
        WHERE se.id = %s AND l.dueno_id = %s AND se.estado_solicitud = 'pendiente'
    """, (id, session['usuario_id']))

    solicitud = cursor.fetchone()
    if not solicitud:
        return jsonify({'error': 'Solicitud no encontrada o no autorizada'}), 404

    usuario_id, local_id, puesto, nombre, correo, password, foto_perfil = solicitud

    # Crea el empleado.
    cursor.execute("""
        INSERT INTO empleados (nombre, correo, password, local_id, puesto, foto_perfil)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (nombre, correo, password, local_id, puesto, foto_perfil))

    mysql.connection.commit()

    # Actualiza el estado de la solicitud.
    cursor.execute("UPDATE solicitudes_empleado SET estado_solicitud = 'aprobado' WHERE id = %s", (id,))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True, 'message': 'Empleado agregado correctamente'})

# ========================================================================
# RUTA: '/api/owner/employee_request/<int:id>/reject' (POST)
# ========================================================================
# DESCRIPCIÓN: RECHAZA UNA SOLICITUD DE EMPLEADO.
# ========================================================================

@app.route('/api/owner/employee_request/<int:id>/reject', methods=['POST'])
@login_required
@rol_requerido(['dueno'])
def owner_reject_employee(id):
    cursor = mysql.connection.cursor()
    # Verifica que la solicitud exista y esté pendiente.
    cursor.execute("""
        SELECT se.id FROM solicitudes_empleado se
        JOIN locales l ON se.local_id = l.id
        WHERE se.id = %s AND l.dueno_id = %s AND se.estado_solicitud = 'pendiente'
    """, (id, session['usuario_id']))

    if not cursor.fetchone():
        return jsonify({'error': 'Solicitud no encontrada o no autorizada'}), 404

    # Marca como rechazada.
    cursor.execute("UPDATE solicitudes_empleado SET estado_solicitud = 'rechazado' WHERE id = %s", (id,))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True, 'message': 'Solicitud rechazada'})

# ========================================================================
# RUTA: '/dueno/pedidos'
# ========================================================================
# DESCRIPCIÓN: VISTA DE PEDIDOS PARA EL DUEÑO.
# ========================================================================

@app.route('/dueno/pedidos')
@login_required
@rol_requerido(['dueno'])
def owner_pedidos():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT nombre FROM locales WHERE dueno_id = %s", (session['usuario_id'],))
    local = cursor.fetchone()
    cursor.close()

    local_nombre = local[0] if local else "Mi Local"
    return render_template('owner_pedidos.html', local_nombre=local_nombre)

# ========================================================================
# RUTAS DE ADMINISTRACIÓN (PANEL, PEDIDOS, SOLICITUDES, GESTIÓN)
# ========================================================================

# ========================================================================
# RUTA: '/admin/panel'
# ========================================================================
# DESCRIPCIÓN: PANEL DE ADMINISTRACIÓN PRINCIPAL.
# ========================================================================

@app.route('/admin/panel')
@login_required
@rol_requerido(['admin'])
def admin_panel():
    return render_template('admin_panel.html')

# ========================================================================
# RUTA: '/admin/pedidos'
# ========================================================================
# DESCRIPCIÓN: VISTA DE TODOS LOS PEDIDOS PARA EL ADMIN.
# ========================================================================

@app.route('/admin/pedidos')
@login_required
@rol_requerido(['admin'])
def admin_pedidos():
    cursor = mysql.connection.cursor()
    # Consulta todos los pedidos con datos del cliente.
    cursor.execute("""
        SELECT p.id, p.codigo, u.nombre, u.correo, p.total, p.fecha, p.estado
        FROM pedidos p
        JOIN usuarios u ON p.usuario_id = u.id
        ORDER BY p.fecha DESC
    """)
    pedidos = cursor.fetchall()
    cursor.close()
    return render_template('admin_pedidos.html', pedidos=pedidos)

# ========================================================================
# RUTA: '/admin/solicitudes'
# ========================================================================
# DESCRIPCIÓN: VISTA DE SOLICITUDES DE DUEÑO PENDIENTES.
# ========================================================================

@app.route('/admin/solicitudes')
@login_required
@rol_requerido(['admin'])
def admin_solicitudes():
    cursor = mysql.connection.cursor()
    # Consulta solicitudes pendientes con datos del dueño.
    cursor.execute("""
        SELECT s.id, s.dueno_id, s.nombre_local, s.ubicacion, s.descripcion,
            s.documento_path, s.estado_solicitud, s.fecha_solicitud,
            d.nombre, d.correo, d.telefono
        FROM solicitudes_dueno s
        JOIN duenos d ON s.dueno_id = d.id
        WHERE s.estado_solicitud = 'pendiente'
        ORDER BY s.fecha_solicitud DESC
    """)
    solicitudes = cursor.fetchall()
    cursor.close()
    return render_template('solicitudes.html', solicitudes=solicitudes)

# ========================================================================
# RUTA: '/admin/gestion'
# ========================================================================
# DESCRIPCIÓN: VISTA DE GESTIÓN ADMINISTRATIVA (CRUD).
# ========================================================================

@app.route('/admin/gestion')
@login_required
@rol_requerido(['admin'])
def admin_gestion():
    return render_template('admin_gestion.html')

# ========================================================================
# RUTAS CRUD DE ADMINISTRACIÓN: PROVEEDORES
# ========================================================================

# ========================================================================
# RUTA: '/api/admin/proveedores' (GET)
# ========================================================================
# DESCRIPCIÓN: LISTA TODOS LOS PROVEEDORES.
# ========================================================================

@app.route('/api/admin/proveedores', methods=['GET'])
@login_required
@rol_requerido(['admin'])
def api_proveedores_list():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, nombre, contacto_nombre, telefono, correo, direccion FROM proveedores ORDER BY id DESC")
    rows = cursor.fetchall()
    cursor.close()

    proveedores = [{
        'id': r[0],
        'nombre': r[1],
        'contacto_nombre': r[2],
        'telefono': r[3],
        'correo': r[4],
        'direccion': r[5]
    } for r in rows]

    return jsonify(proveedores)

# ========================================================================
# RUTA: '/api/admin/proveedores/<int:id>' (GET)
# ========================================================================
# DESCRIPCIÓN: OBTIENE UN PROVEEDOR POR SU ID.
# ========================================================================

@app.route('/api/admin/proveedores/<int:id>', methods=['GET'])
@login_required
@rol_requerido(['admin'])
def api_proveedor_get(id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, nombre, contacto_nombre, telefono, correo, direccion FROM proveedores WHERE id=%s", (id,))
    row = cursor.fetchone()
    cursor.close()

    if not row:
        return jsonify({'error': 'Proveedor no encontrado'}), 404

    return jsonify({
        'id': row[0],
        'nombre': row[1],
        'contacto_nombre': row[2],
        'telefono': row[3],
        'correo': row[4],
        'direccion': row[5]
    })

# ========================================================================
# RUTA: '/api/admin/proveedores' (POST)
# ========================================================================
# DESCRIPCIÓN: CREA UN NUEVO PROVEEDOR.
# ========================================================================

@app.route('/api/admin/proveedores', methods=['POST'])
@login_required
@rol_requerido(['admin'])
def api_proveedor_create():
    data = request.json
    cursor = mysql.connection.cursor()
    cursor.execute("""
        INSERT INTO proveedores (nombre, contacto_nombre, telefono, correo, direccion)
        VALUES (%s, %s, %s, %s, %s)
    """, (data['nombre'], data.get('contacto_nombre'), data.get('telefono'), data.get('correo'), data.get('direccion')))
    mysql.connection.commit()
    new_id = cursor.lastrowid
    cursor.close()
    return jsonify({'id': new_id, 'message': 'Proveedor creado'}), 201

# ========================================================================
# RUTA: '/api/admin/proveedores/<int:id>' (PUT)
# ========================================================================
# DESCRIPCIÓN: ACTUALIZA UN PROVEEDOR.
# ========================================================================

@app.route('/api/admin/proveedores/<int:id>', methods=['PUT'])
@login_required
@rol_requerido(['admin'])
def api_proveedor_update(id):
    data = request.json
    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE proveedores
        SET nombre=%s, contacto_nombre=%s, telefono=%s, correo=%s, direccion=%s
        WHERE id=%s
    """, (data['nombre'], data.get('contacto_nombre'), data.get('telefono'), data.get('correo'), data.get('direccion'), id))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'message': 'Proveedor actualizado'})

# ========================================================================
# RUTA: '/api/admin/proveedores/<int:id>' (DELETE)
# ========================================================================
# DESCRIPCIÓN: ELIMINA UN PROVEEDOR.
# ========================================================================

@app.route('/api/admin/proveedores/<int:id>', methods=['DELETE'])
@login_required
@rol_requerido(['admin'])
def api_proveedor_delete(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM proveedores WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'message': 'Proveedor eliminado'})

# ========================================================================
# RUTAS CRUD DE ADMINISTRACIÓN: DUEÑOS
# ========================================================================

# ========================================================================
# RUTA: '/api/admin/duenos' (GET)
# ========================================================================
# DESCRIPCIÓN: LISTA TODOS LOS DUEÑOS CON SU LOCAL.
# ========================================================================

@app.route('/api/admin/duenos', methods=['GET'])
@login_required
@rol_requerido(['admin'])
def api_duenos_list():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT d.id, d.nombre, d.correo, d.documento_identidad, d.direccion,
            l.nombre as local_nombre, l.codigo as codigo_local, l.categoria
        FROM duenos d
        LEFT JOIN locales l ON d.id = l.dueno_id
        ORDER BY d.id DESC
    """)
    rows = cursor.fetchall()
    cursor.close()

    duenos = [{
        'id': r[0],
        'nombre': r[1],
        'correo': r[2],
        'documento_identidad': r[3],
        'direccion': r[4],
        'nombre_local': r[5],
        'codigo_local': r[6],
        'categoria': r[7]
    } for r in rows]

    return jsonify(duenos)

# ========================================================================
# RUTA: '/api/admin/duenos' (POST)
# ========================================================================
# DESCRIPCIÓN: CREA UN NUEVO DUEÑO Y SU LOCAL.
# ========================================================================

@app.route('/api/admin/duenos', methods=['POST'])
@login_required
@rol_requerido(['admin'])
def api_dueno_create():
    data = request.json
    cursor = mysql.connection.cursor()

    try:
        # Inserta el dueño con contraseña temporal.
        cursor.execute("""
            INSERT INTO duenos (nombre, correo, documento_identidad, direccion, password, estado)
            VALUES (%s, %s, %s, %s, 'temp123', 'activo')
        """, (data['nombre'], data['correo'], data.get('documento_identidad', ''), data.get('direccion', '')))
        dueno_id = cursor.lastrowid

        # Crea el local asociado.
        nombre_local = data.get('nombre_local', data['nombre'])
        codigo = data.get('codigo_local', nombre_local[:3].upper() + str(dueno_id))
        cursor.execute("""
            INSERT INTO locales (codigo, nombre, dueno_id, categoria, dias_stock)
            VALUES (%s, %s, %s, %s, %s)
        """, (codigo, nombre_local, dueno_id, data.get('categoria', ''), data.get('dias_stock', '')))

        mysql.connection.commit()
        cursor.close()
        return jsonify({'id': dueno_id, 'message': 'Comerciante y local creados'}), 201

    except MySQLdb.IntegrityError as e:
        mysql.connection.rollback()
        if e.args[0] == 1062:
            return jsonify({'error': 'El correo ya está registrado'}), 400
        return jsonify({'error': 'Error de integridad'}), 400
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500

# ========================================================================
# RUTA: '/api/admin/duenos/<int:id>' (GET)
# ========================================================================
# DESCRIPCIÓN: OBTIENE UN DUEÑO POR SU ID.
# ========================================================================

@app.route('/api/admin/duenos/<int:id>', methods=['GET'])
@login_required
@rol_requerido(['admin'])
def api_dueno_get(id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT d.id, d.nombre, d.correo, d.documento_identidad, d.telefono, d.estado, d.direccion,
            l.nombre as local_nombre, l.codigo as codigo_local, l.categoria, l.dias_stock
        FROM duenos d
        LEFT JOIN locales l ON d.id = l.dueno_id
        WHERE d.id=%s
    """, (id,))
    row = cursor.fetchone()
    cursor.close()

    if not row:
        return jsonify({'error': 'Dueño no encontrado'}), 404

    return jsonify({
        'id': row[0],
        'nombre': row[1],
        'correo': row[2],
        'documento_identidad': row[3],
        'telefono': row[4],
        'estado': row[5],
        'direccion': row[6],
        'nombre_local': row[7],
        'codigo_local': row[8],
        'categoria': row[9],
        'dias_stock': row[10]
    })

# ========================================================================
# RUTA: '/api/admin/duenos/<int:id>' (PUT)
# ========================================================================
# DESCRIPCIÓN: ACTUALIZA UN DUEÑO Y SU LOCAL.
# ========================================================================

@app.route('/api/admin/duenos/<int:id>', methods=['PUT'])
@login_required
@rol_requerido(['admin'])
def api_dueno_update(id):
    data = request.json
    cursor = mysql.connection.cursor()

    try:
        # Actualiza el dueño.
        cursor.execute("""
            UPDATE duenos
            SET nombre=%s, correo=%s, documento_identidad=%s, direccion=%s
            WHERE id=%s
        """, (data['nombre'], data['correo'], data.get('documento_identidad', ''), data.get('direccion', ''), id))

        # Verifica si tiene local y lo actualiza.
        cursor.execute("SELECT id FROM locales WHERE dueno_id=%s", (id,))
        local = cursor.fetchone()

        if local:
            cursor.execute("""
                UPDATE locales
                SET nombre=%s, codigo=%s, categoria=%s, dias_stock=%s
                WHERE dueno_id=%s
            """, (data.get('nombre_local'), data.get('codigo_local'), data.get('categoria'), data.get('dias_stock'), id))

        mysql.connection.commit()
        cursor.close()
        return jsonify({'message': 'Dueño actualizado'})

    except MySQLdb.IntegrityError as e:
        mysql.connection.rollback()
        if e.args[0] == 1062:
            return jsonify({'error': 'El correo ya está registrado'}), 400
        return jsonify({'error': 'Error de integridad'}), 400
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({'error': str(e)}), 500

# ========================================================================
# RUTA: '/api/admin/duenos/<int:id>' (DELETE)
# ========================================================================
# DESCRIPCIÓN: ELIMINA UN DUEÑO Y SU LOCAL.
# ========================================================================

@app.route('/api/admin/duenos/<int:id>', methods=['DELETE'])
@login_required
@rol_requerido(['admin'])
def api_dueno_delete(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM locales WHERE dueno_id=%s", (id,))
    cursor.execute("DELETE FROM duenos WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'message': 'Dueño eliminado'})

# ========================================================================
# RUTAS CRUD DE ADMINISTRACIÓN: EMPLEADOS
# ========================================================================

# ========================================================================
# RUTA: '/api/admin/empleados' (GET)
# ========================================================================
# DESCRIPCIÓN: LISTA TODOS LOS EMPLEADOS.
# ========================================================================

@app.route('/api/admin/empleados', methods=['GET'])
@login_required
@rol_requerido(['admin'])
def api_empleados_list():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT e.id, e.nombre, e.correo, e.rol, e.local_id, l.nombre as local_nombre
        FROM empleados e
        LEFT JOIN locales l ON e.local_id = l.id
        ORDER BY e.id DESC
    """)
    rows = cursor.fetchall()
    cursor.close()

    empleados = [{
        'id': r[0],
        'nombre': r[1],
        'correo': r[2],
        'rol': r[3],
        'local_id': r[4],
        'local_nombre': r[5]
    } for r in rows]

    return jsonify(empleados)

# ========================================================================
# RUTA: '/api/admin/empleados' (POST)
# ========================================================================
# DESCRIPCIÓN: CREA UN EMPLEADO CON CONTRASEÑA TEMPORAL.
# ========================================================================

@app.route('/api/admin/empleados', methods=['POST'])
@login_required
@rol_requerido(['admin'])
def api_empleado_create():
    data = request.json
    # Genera una contraseña temporal aleatoria.
    password_temp = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

    cursor = mysql.connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO empleados (nombre, correo, password, local_id, puesto, rol)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (data['nombre'], data['correo'], generate_password_hash(password_temp), data.get('local_id'), data.get('puesto', ''), data.get('rol', 'empleado')))
        mysql.connection.commit()
        cursor.close()
        return jsonify({'message': 'Empleado creado', 'temp_password': password_temp}), 201

    except MySQLdb.IntegrityError as e:
        mysql.connection.rollback()
        if e.args[0] == 1062:
            return jsonify({'error': 'El correo ya está registrado'}), 400
        return jsonify({'error': 'Error de integridad'}), 400

# ========================================================================
# RUTA: '/api/admin/empleados/<int:id>' (GET)
# ========================================================================
# DESCRIPCIÓN: OBTIENE UN EMPLEADO POR SU ID.
# ========================================================================

@app.route('/api/admin/empleados/<int:id>', methods=['GET'])
@login_required
@rol_requerido(['admin'])
def api_empleado_get(id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT e.id, e.nombre, e.correo, e.rol, e.local_id, e.telefono, e.puesto
        FROM empleados e
        WHERE e.id=%s
    """, (id,))
    row = cursor.fetchone()
    cursor.close()

    if not row:
        return jsonify({'error': 'Empleado no encontrado'}), 404

    return jsonify({
        'id': row[0],
        'nombre': row[1],
        'correo': row[2],
        'rol': row[3],
        'local_id': row[4],
        'telefono': row[5],
        'puesto': row[6]
    })

# ========================================================================
# RUTA: '/api/admin/empleados/<int:id>' (PUT)
# ========================================================================
# DESCRIPCIÓN: ACTUALIZA UN EMPLEADO.
# ========================================================================

@app.route('/api/admin/empleados/<int:id>', methods=['PUT'])
@login_required
@rol_requerido(['admin'])
def api_empleado_update(id):
    data = request.json
    cursor = mysql.connection.cursor()
    cursor.execute("""
        UPDATE empleados
        SET nombre=%s, correo=%s, rol=%s, local_id=%s, puesto=%s
        WHERE id=%s
    """, (data['nombre'], data['correo'], data.get('rol', 'empleado'), data.get('local_id'), data.get('puesto', ''), id))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'message': 'Empleado actualizado'})

# ========================================================================
# RUTA: '/api/admin/empleados/<int:id>' (DELETE)
# ========================================================================
# DESCRIPCIÓN: ELIMINA UN EMPLEADO.
# ========================================================================

@app.route('/api/admin/empleados/<int:id>', methods=['DELETE'])
@login_required
@rol_requerido(['admin'])
def api_empleado_delete(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM empleados WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'message': 'Empleado eliminado'})

# ========================================================================
# RUTAS ADMIN: ESTADÍSTICAS Y DATOS GLOBALES (API)
# ========================================================================

# ========================================================================
# RUTA: '/api/admin/stats' (GET)
# ========================================================================
# DESCRIPCIÓN: DEVUELVE ESTADÍSTICAS GLOBALES DEL SISTEMA.
# ========================================================================

@app.route('/api/admin/stats')
@login_required
@rol_requerido(['admin'])
def admin_stats():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM pedidos")
    total_orders = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM productos")
    total_products = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM locales")
    total_locales = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM solicitudes_dueno WHERE estado_solicitud='pendiente'")
    pending_requests = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(total) FROM pedidos WHERE estado='entregado'")
    total_revenue = cursor.fetchone()[0] or 0

    cursor.close()

    return jsonify({
        'total_users': total_users,
        'total_orders': total_orders,
        'total_products': total_products,
        'total_locales': total_locales,
        'pending_requests': pending_requests,
        'total_revenue': float(total_revenue)
    })

# ========================================================================
# RUTA: '/api/admin/users' (GET)
# ========================================================================
# DESCRIPCIÓN: LISTA TODOS LOS USUARIOS (CLIENTES, DUEÑOS, EMPLEADOS, ADMINS).
# ========================================================================

@app.route('/api/admin/users')
@login_required
@rol_requerido(['admin'])
def admin_users():
    cursor = mysql.connection.cursor()

    # Clientes
    cursor.execute("SELECT id, nombre, correo, 'cliente' as rol, estado, IFNULL(documento_identidad, '') as doc, IFNULL(direccion, '') as dir, IFNULL(foto_perfil, '') as foto FROM usuarios")
    clientes = [{'id': row[0], 'nombre': row[1], 'correo': row[2], 'rol': row[3], 'estado': row[4],
                'documento_identidad': row[5], 'direccion': row[6], 'foto_perfil': row[7]} for row in cursor.fetchall()]

    # Dueños
    cursor.execute("SELECT id, nombre, correo, 'dueno' as rol, estado, IFNULL(documento_identidad, '') as doc, IFNULL(direccion, '') as dir, IFNULL(foto_perfil, '') as foto FROM duenos")
    duenos = [{'id': row[0], 'nombre': row[1], 'correo': row[2], 'rol': row[3], 'estado': row[4],
            'documento_identidad': row[5], 'direccion': row[6], 'foto_perfil': row[7]} for row in cursor.fetchall()]

    # Empleados
    cursor.execute("SELECT id, nombre, correo, 'empleado' as rol, 'activo' as estado, '' as doc, '' as dir, IFNULL(foto_perfil, '') as foto FROM empleados")
    empleados = [{'id': row[0], 'nombre': row[1], 'correo': row[2], 'rol': row[3], 'estado': row[4],
                'documento_identidad': row[5], 'direccion': row[6], 'foto_perfil': row[7]} for row in cursor.fetchall()]

    # Administradores
    cursor.execute("SELECT id, nombre, correo, 'admin' as rol, estado, '' as doc, '' as dir, IFNULL(foto_perfil, '') as foto FROM administradores")
    admins = [{'id': row[0], 'nombre': row[1], 'correo': row[2], 'rol': row[3], 'estado': row[4],
            'documento_identidad': row[5], 'direccion': row[6], 'foto_perfil': row[7]} for row in cursor.fetchall()]

    cursor.close()

    # Combina todas las listas.
    users = clientes + duenos + empleados + admins

    # Agrega URL de imagen de perfil si existe en MongoDB.
    for u in users:
        u['imagen_url'] = f"/imagen/usuario/{u['id']}" if tiene_imagen('usuario', u['id']) else None

    return jsonify(users)

# ========================================================================
# RUTA: '/api/admin/locales' (GET)
# ========================================================================
# DESCRIPCIÓN: LISTA TODOS LOS LOCALES.
# ========================================================================

@app.route('/api/admin/locales')
@login_required
@rol_requerido(['admin'])
def admin_locales():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, codigo, nombre, dueno_id, categoria, dias_stock FROM locales")
    locales = []
    for row in cursor.fetchall():
        local_id = row[0]
        locales.append({
            'id': local_id,
            'codigo': row[1],
            'nombre': row[2],
            'usuario_id': row[3],
            'categoria': row[4],
            'dias_stock': row[5],
            'imagen_url': f"/imagen/local/{local_id}" if tiene_imagen('local', local_id) else None
        })
    cursor.close()
    return jsonify(locales)

# ========================================================================
# RUTA: '/api/admin/products' (GET)
# ========================================================================
# DESCRIPCIÓN: LISTA TODOS LOS PRODUCTOS.
# ========================================================================

@app.route('/api/admin/products')
@login_required
@rol_requerido(['admin'])
def admin_products():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, nombre, precio, stock, local_id FROM productos")
    products = []
    for row in cursor.fetchall():
        producto_id = row[0]
        products.append({
            'id': producto_id,
            'nombre': row[1],
            'precio': float(row[2]),
            'stock': row[3],
            'local_id': row[4],
            'imagen_url': f"/imagen/producto/{producto_id}" if tiene_imagen('producto', producto_id) else None
        })
    cursor.close()
    return jsonify(products)

# ========================================================================
# RUTA: '/api/admin/orders' (GET)
# ========================================================================
# DESCRIPCIÓN: LISTA TODOS LOS PEDIDOS CON CLIENTE.
# ========================================================================

@app.route('/api/admin/orders')
@login_required
@rol_requerido(['admin'])
def admin_orders():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT p.id, p.codigo, u.nombre, p.total, p.estado
        FROM pedidos p JOIN usuarios u ON p.usuario_id = u.id
        ORDER BY p.id DESC
    """)
    orders = [{'id': row[0], 'codigo': row[1], 'cliente': row[2], 'total': float(row[3]), 'estado': row[4]} for row in cursor.fetchall()]
    cursor.close()
    return jsonify(orders)

# ========================================================================
# RUTA: '/api/admin/requests' (GET)
# ========================================================================
# DESCRIPCIÓN: LISTA SOLICITUDES DE DUEÑO PENDIENTES.
# ========================================================================

@app.route('/api/admin/requests')
@login_required
@rol_requerido(['admin'])
def admin_requests():
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT s.id, s.nombre_local, s.ubicacion, s.descripcion, s.documento_path, d.nombre, d.correo
        FROM solicitudes_dueno s JOIN duenos d ON s.dueno_id = d.id
        WHERE s.estado_solicitud = 'pendiente'
    """)
    requests = [{'id': row[0], 'nombre_local': row[1], 'ubicacion': row[2], 'descripcion': row[3],
                'documento_path': row[4], 'usuario_nombre': row[5], 'usuario_correo': row[6]} for row in cursor.fetchall()]
    cursor.close()
    return jsonify(requests)

# ========================================================================
# RUTAS ADMIN: OPERACIONES CRUD (DELETE, UPDATE, GET)
# ========================================================================

# ========================================================================
# RUTA: '/api/admin/user/<int:id>' (DELETE)
# ========================================================================
# DESCRIPCIÓN: ELIMINA UN USUARIO DE TODAS LAS TABLAS POSIBLES.
# ========================================================================

@app.route('/api/admin/user/<int:id>', methods=['DELETE'])
@login_required
@rol_requerido(['admin'])
def admin_delete_user(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM usuarios WHERE id=%s", (id,))
    cursor.execute("DELETE FROM duenos WHERE id=%s", (id,))
    cursor.execute("DELETE FROM empleados WHERE id=%s", (id,))
    cursor.execute("DELETE FROM administradores WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True})

# ========================================================================
# RUTA: '/api/admin/user/<int:id>' (GET)
# ========================================================================
# DESCRIPCIÓN: OBTIENE UN USUARIO POR ID (BUSCA EN TODAS LAS TABLAS).
# ========================================================================

@app.route('/api/admin/user/<int:id>', methods=['GET'])
@login_required
@rol_requerido(['admin'])
def admin_get_user(id):
    cursor = mysql.connection.cursor()

    # Busca en usuarios (clientes).
    cursor.execute("SELECT id, nombre, correo, 'cliente' as rol, estado, documento_identidad, direccion, foto_perfil FROM usuarios WHERE id=%s", (id,))
    user = cursor.fetchone()

    if user:
        cursor.close()
        return jsonify({
            'id': user[0],
            'nombre': user[1],
            'correo': user[2],
            'rol': user[3],
            'estado': user[4],
            'documento_identidad': user[5] or '',
            'direccion': user[6] or '',
            'foto_perfil': user[7] or '',
            'imagen_url': f"/imagen/usuario/{id}" if tiene_imagen('usuario', id) else None
        })

    # Busca en duenos.
    cursor.execute("SELECT id, nombre, correo, 'dueno' as rol, estado, documento_identidad, direccion, foto_perfil FROM duenos WHERE id=%s", (id,))
    dueno = cursor.fetchone()

    if dueno:
        cursor.close()
        return jsonify({
            'id': dueno[0],
            'nombre': dueno[1],
            'correo': dueno[2],
            'rol': dueno[3],
            'estado': dueno[4],
            'documento_identidad': dueno[5] or '',
            'direccion': dueno[6] or '',
            'foto_perfil': dueno[7] or '',
            'imagen_url': f"/imagen/usuario/{id}" if tiene_imagen('usuario', id) else None
        })

    cursor.close()
    return jsonify({'error': 'Usuario no encontrado'}), 404

# ========================================================================
# RUTA: '/api/admin/local/<int:id>' (DELETE)
# ========================================================================
# DESCRIPCIÓN: ELIMINA UN LOCAL.
# ========================================================================

@app.route('/api/admin/local/<int:id>', methods=['DELETE'])
@login_required
@rol_requerido(['admin'])
def admin_delete_local(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM locales WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True})

# ========================================================================
# RUTA: '/api/admin/product/<int:id>' (DELETE)
# ========================================================================
# DESCRIPCIÓN: ELIMINA UN PRODUCTO.
# ========================================================================

@app.route('/api/admin/product/<int:id>', methods=['DELETE'])
@login_required
@rol_requerido(['admin'])
def admin_delete_product(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM productos WHERE id=%s", (id,))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True})

# ========================================================================
# RUTA: '/api/admin/request/<int:id>/approve' (POST)
# ========================================================================
# DESCRIPCIÓN: APRUEBA UNA SOLICITUD DE DUEÑO VÍA API.
# ========================================================================

@app.route('/api/admin/request/<int:id>/approve', methods=['POST'])
@login_required
@rol_requerido(['admin'])
def admin_approve_request(id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT dueno_id, nombre_local, ubicacion, descripcion FROM solicitudes_dueno WHERE id=%s", (id,))
    sol = cursor.fetchone()

    if sol:
        dueno_id, nombre_local, ubicacion, descripcion_negocio = sol
        cursor.execute("UPDATE duenos SET estado='activo' WHERE id=%s", (dueno_id,))
        codigo = nombre_local[:3].upper() + str(dueno_id)
        cursor.execute("INSERT INTO locales (codigo, nombre, descripcion, ubicacion, dueno_id, categoria, dias_stock) VALUES (%s, %s, %s, %s, %s, '', '')",
                    (codigo, nombre_local, descripcion_negocio, ubicacion, dueno_id))
        cursor.execute("UPDATE solicitudes_dueno SET estado_solicitud='aprobado' WHERE id=%s", (id,))
        mysql.connection.commit()

    cursor.close()
    return jsonify({'success': True})

# ========================================================================
# RUTA: '/api/admin/request/<int:id>/reject' (POST)
# ========================================================================
# DESCRIPCIÓN: RECHAZA UNA SOLICITUD DE DUEÑO VÍA API.
# ========================================================================

@app.route('/api/admin/request/<int:id>/reject', methods=['POST'])
@login_required
@rol_requerido(['admin'])
def admin_reject_request(id):
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE solicitudes_dueno SET estado_solicitud='rechazado' WHERE id=%s", (id,))
    cursor.execute("UPDATE duenos SET estado='inactivo' WHERE id=(SELECT dueno_id FROM solicitudes_dueno WHERE id=%s)", (id,))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True})

# ========================================================================
# RUTA: '/api/admin/user/<int:id>' (PUT)
# ========================================================================
# DESCRIPCIÓN: ACTUALIZA DOCUMENTO Y DIRECCIÓN DE UN USUARIO.
# ========================================================================

@app.route('/api/admin/user/<int:id>', methods=['PUT'])
@login_required
@rol_requerido(['admin'])
def admin_update_user(id):
    data = request.get_json()
    documento = data.get('documento_identidad')
    direccion = data.get('direccion')

    cursor = mysql.connection.cursor()
    # Busca en usuarios (clientes).
    cursor.execute("SELECT id FROM usuarios WHERE id=%s", (id,))
    if cursor.fetchone():
        cursor.execute("UPDATE usuarios SET documento_identidad=%s, direccion=%s WHERE id=%s", (documento, direccion, id))
    else:
        # Busca en duenos.
        cursor.execute("SELECT id FROM duenos WHERE id=%s", (id,))
        if cursor.fetchone():
            cursor.execute("UPDATE duenos SET documento_identidad=%s, direccion=%s WHERE id=%s", (documento, direccion, id))

    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True})

# ========================================================================
# RUTA: '/api/admin/local/<int:id>' (PUT)
# ========================================================================
# DESCRIPCIÓN: ACTUALIZA UN LOCAL.
# ========================================================================

@app.route('/api/admin/local/<int:id>', methods=['PUT'])
@login_required
@rol_requerido(['admin'])
def admin_update_local(id):
    data = request.get_json()
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE locales SET nombre=%s, codigo=%s, categoria=%s, dias_stock=%s WHERE id=%s",
                (data['nombre'], data['codigo'], data.get('categoria', ''), data.get('dias_stock', ''), id))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True})

# ========================================================================
# RUTA: '/api/admin/product/<int:id>' (PUT)
# ========================================================================
# DESCRIPCIÓN: ACTUALIZA UN PRODUCTO.
# ========================================================================

@app.route('/api/admin/product/<int:id>', methods=['PUT'])
@login_required
@rol_requerido(['admin'])
def admin_update_product(id):
    data = request.get_json()
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE productos SET nombre=%s, precio=%s, stock=%s WHERE id=%s",
                (data['nombre'], data['precio'], data['stock'], id))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True})

# ========================================================================
# RUTA: '/api/admin/order/<int:id>/status' (POST)
# ========================================================================
# DESCRIPCIÓN: ACTUALIZA EL ESTADO DE UN PEDIDO (ADMIN).
# ========================================================================

@app.route('/api/admin/order/<int:id>/status', methods=['POST'])
@login_required
@rol_requerido(['admin'])
def admin_update_order_status(id):
    data = request.get_json()
    nuevo_estado = data.get('estado')

    if nuevo_estado not in ('pendiente', 'listo', 'entregado', 'cancelado'):
        return jsonify({'success': False, 'message': 'Estado inválido'}), 400

    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE pedidos SET estado=%s WHERE id=%s", (nuevo_estado, id))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True, 'message': 'Estado actualizado'})

# ========================================================================
# RUTA: '/api/admin/settings' (POST)
# ========================================================================
# DESCRIPCIÓN: GUARDA CONFIGURACIONES GLOBALES (PLACEHOLDER).
# ========================================================================

@app.route('/api/admin/settings', methods=['POST'])
@login_required
@rol_requerido(['admin'])
def admin_settings():
    data = request.get_json()
    # Aquí se pueden guardar configuraciones globales en una tabla de settings.
    # Por ahora solo retorna éxito.
    return jsonify({'success': True})

# ========================================================================
# RUTAS PARA EMPLEADO (PANEL LIMITADO)
# ========================================================================

# ========================================================================
# RUTA: '/api/empleado/stats' (GET)
# ========================================================================
# DESCRIPCIÓN: DEVUELVE ESTADÍSTICAS DEL LOCAL DEL EMPLEADO.
# ========================================================================

@app.route('/api/empleado/stats')
@login_required
@rol_requerido(['empleado'])
def empleado_stats():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT local_id FROM empleados WHERE id=%s", (session['usuario_id'],))
    local = cursor.fetchone()

    if not local:
        return jsonify({'error': 'No local assigned'}), 404

    local_id = local[0]

    # Pedidos de hoy.
    cursor.execute("SELECT COUNT(*) FROM pedidos WHERE local_id=%s AND DATE(fecha)=CURDATE()", (local_id,))
    pedidos_hoy = cursor.fetchone()[0]

    # Pedidos pendientes.
    cursor.execute("SELECT COUNT(*) FROM pedidos WHERE local_id=%s AND estado='pendiente'", (local_id,))
    pendientes = cursor.fetchone()[0]

    # Pedidos listos.
    cursor.execute("SELECT COUNT(*) FROM pedidos WHERE local_id=%s AND estado='listo'", (local_id,))
    listos = cursor.fetchone()[0]

    cursor.close()

    return jsonify({
        'pedidos_hoy': pedidos_hoy,
        'pendientes': pendientes,
        'listos': listos
    })

# ========================================================================
# RUTA: '/api/empleado/pedidos' (GET)
# ========================================================================
# DESCRIPCIÓN: LISTA LOS PEDIDOS DEL LOCAL DEL EMPLEADO.
# ========================================================================

@app.route('/api/empleado/pedidos')
@login_required
@rol_requerido(['empleado'])
def empleado_pedidos():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT local_id FROM empleados WHERE id=%s", (session['usuario_id'],))
    local = cursor.fetchone()

    if not local:
        return jsonify([])

    local_id = local[0]

    cursor.execute("""
        SELECT p.id, p.codigo, u.nombre, p.total, p.estado
        FROM pedidos p
        JOIN usuarios u ON p.usuario_id = u.id
        WHERE p.local_id = %s
        ORDER BY p.fecha DESC
    """, (local_id,))

    pedidos = [{'id': row[0], 'codigo': row[1], 'cliente': row[2], 'total': float(row[3]), 'estado': row[4]} for row in cursor.fetchall()]
    cursor.close()
    return jsonify(pedidos)

# ========================================================================
# RUTA: '/api/empleado/pedido/<int:id>/estado' (PUT)
# ========================================================================
# DESCRIPCIÓN: ACTUALIZA EL ESTADO DE UN PEDIDO (EMPLEADO).
# ========================================================================

@app.route('/api/empleado/pedido/<int:id>/estado', methods=['PUT'])
@login_required
@rol_requerido(['empleado'])
def empleado_update_pedido_estado(id):
    data = request.get_json()
    nuevo_estado = data.get('estado')

    if nuevo_estado not in ('pendiente', 'listo', 'entregado', 'cancelado'):
        return jsonify({'error': 'Estado inválido'}), 400

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT local_id FROM pedidos WHERE id=%s", (id,))
    pedido = cursor.fetchone()

    if not pedido:
        return jsonify({'error': 'Pedido no encontrado'}), 404

    # Verifica que el pedido pertenezca al local del empleado.
    cursor.execute("SELECT local_id FROM empleados WHERE id=%s", (session['usuario_id'],))
    empleado_local = cursor.fetchone()

    if not empleado_local or empleado_local[0] != pedido[0]:
        return jsonify({'error': 'No autorizado'}), 403

    cursor.execute("UPDATE pedidos SET estado=%s WHERE id=%s", (nuevo_estado, id))
    mysql.connection.commit()
    cursor.close()
    return jsonify({'success': True})

# ========================================================================
# RUTA: '/api/empleado/productos' (GET)
# ========================================================================
# DESCRIPCIÓN: LISTA LOS PRODUCTOS DEL LOCAL DEL EMPLEADO.
# ========================================================================

@app.route('/api/empleado/productos')
@login_required
@rol_requerido(['empleado'])
def empleado_productos():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT local_id FROM empleados WHERE id=%s", (session['usuario_id'],))
    local = cursor.fetchone()

    if not local:
        return jsonify([])

    local_id = local[0]

    cursor.execute("SELECT id, nombre, precio, stock FROM productos WHERE local_id=%s ORDER BY nombre", (local_id,))
    productos = []
    for row in cursor.fetchall():
        producto_id = row[0]
        productos.append({
            'id': producto_id,
            'nombre': row[1],
            'precio': float(row[2]),
            'stock': row[3],
            'imagen_url': f"/imagen/producto/{producto_id}" if tiene_imagen('producto', producto_id) else None
        })

    cursor.close()
    return jsonify(productos)

# ========================================================================
# RUTA: '/api/empleado/pedido/mostrador' (POST)
# ========================================================================
# DESCRIPCIÓN: CREA UN PEDIDO DESDE EL MOSTRADOR (EMPLEADO).
# ========================================================================

@app.route('/api/empleado/pedido/mostrador', methods=['POST'])
@login_required
@rol_requerido(['empleado'])
def empleado_pedido_mostrador():
    data = request.get_json()
    cliente_correo = data.get('cliente_correo')
    productos_data = data.get('productos', [])

    if not cliente_correo or not productos_data:
        return jsonify({'error': 'Datos incompletos'}), 400

    cursor = mysql.connection.cursor()
    cursor.execute("SELECT local_id FROM empleados WHERE id=%s", (session['usuario_id'],))
    empleado_local = cursor.fetchone()

    if not empleado_local:
        return jsonify({'error': 'No tienes local asignado'}), 403

    local_id = empleado_local[0]

    # Busca o crea el cliente en la tabla usuarios.
    cursor.execute("SELECT id, nombre FROM usuarios WHERE correo=%s", (cliente_correo,))
    cliente = cursor.fetchone()

    if not cliente:
        # Si no existe, crea un usuario cliente temporal.
        nombre_temp = cliente_correo.split('@')[0]
        cursor.execute("""
            INSERT INTO usuarios (nombre, correo, password, fecha_nacimiento, telefono, estado)
            VALUES (%s, %s, 'cliente_temp', '2000-01-01', '', 'activo')
        """, (nombre_temp, cliente_correo))
        mysql.connection.commit()
        cliente_id = cursor.lastrowid
        cliente_nombre = nombre_temp
    else:
        cliente_id = cliente[0]
        cliente_nombre = cliente[1]

    total = 0
    items = []

    try:
        # Inicia transacción para asegurar consistencia.
        cursor.execute("START TRANSACTION")

        for item in productos_data:
            # Bloquea el producto para actualización.
            cursor.execute("SELECT nombre, precio, stock FROM productos WHERE id=%s AND local_id=%s FOR UPDATE", (item['id'], local_id))
            prod = cursor.fetchone()
            if not prod:
                raise Exception(f'Producto {item["id"]} no existe en tu local')

            if prod[2] < item['cantidad']:
                raise Exception(f'Stock insuficiente para {prod[0]}')

            # Actualiza el stock.
            nuevo_stock = prod[2] - item['cantidad']
            cursor.execute("UPDATE productos SET stock=%s WHERE id=%s", (nuevo_stock, item['id']))

            items.append({
                'id': item['id'],
                'nombre': prod[0],
                'precio': float(prod[1]),
                'cantidad': item['cantidad']
            })
            total += float(prod[1]) * item['cantidad']

        # Genera código y crea el pedido.
        codigo = generar_codigo_pedido()
        cursor.execute("""
            INSERT INTO pedidos (codigo, usuario_id, total, estado, local_id)
            VALUES (%s, %s, %s, 'pendiente', %s)
        """, (codigo, cliente_id, total, local_id))
        pedido_id = cursor.lastrowid

        # Inserta los detalles del pedido.
        for item in items:
            cursor.execute("""
                INSERT INTO detalle_pedido (pedido_id, producto_id, cantidad, precio_unitario)
                VALUES (%s, %s, %s, %s)
            """, (pedido_id, item['id'], item['cantidad'], item['precio']))

        mysql.connection.commit()
        cursor.close()
        return jsonify({'success': True, 'codigo': codigo, 'total': total})

    except Exception as e:
        cursor.execute("ROLLBACK")
        cursor.close()
        return jsonify({'error': str(e)}), 500

# ========================================================================
# RUTAS API DE FAVORITOS (ACTUALIZADAS CON TIPO_USUARIO)
# ========================================================================

# ========================================================================
# RUTA: '/api/favoritos' (GET)
# ========================================================================
# DESCRIPCIÓN: OBTIENE LA LISTA DE PRODUCTOS FAVORITOS DEL USUARIO,
# FILTRANDO POR EL TIPO DE USUARIO (CLIENTE, DUEÑO, EMPLEADO, ADMIN)
# PARA QUE CADA ROL TENGA SUS PROPIOS FAVORITOS DE MANERA INDEPENDIENTE.
# ========================================================================

@app.route('/api/favoritos', methods=['GET'])
@login_required
def api_favoritos_get():
    # Se crea un cursor para ejecutar consultas SQL.
    cursor = mysql.connection.cursor()
    # Se ejecuta una consulta SELECT para obtener los IDs de los productos
    # favoritos del usuario actual, filtrando por usuario_id y tipo_usuario.
    # El tipo_usuario se obtiene de la sesión (session['tipo_tabla']).
    cursor.execute(
        "SELECT producto_id FROM favoritos WHERE usuario_id=%s AND tipo_usuario=%s",
        (session['usuario_id'], session.get('tipo_tabla'))
    )
    # Se extraen los IDs de los productos de cada fila y se almacenan en una lista.
    favs = [row[0] for row in cursor.fetchall()]
    # Se cierra el cursor para liberar recursos.
    cursor.close()
    # Se retorna la lista de favoritos en formato JSON.
    return jsonify({'favoritos': favs})

# ========================================================================
# RUTA: '/api/favoritos/agregar' (POST)
# ========================================================================
# DESCRIPCIÓN: AGREGA UN PRODUCTO A FAVORITOS PARA EL USUARIO Y SU ROL.
# ========================================================================

@app.route('/api/favoritos/agregar', methods=['POST'])
@login_required
def api_favoritos_agregar():
    # Se obtienen los datos JSON enviados en la solicitud.
    data = request.get_json()
    # Se extrae el ID del producto a agregar.
    producto_id = data.get('producto_id')
    # Si no se proporciona el ID, se retorna un error.
    if not producto_id:
        return jsonify({'error': 'Falta producto_id'}), 400

    # Se obtiene el ID del usuario desde la sesión.
    usuario_id = session['usuario_id']
    # Se obtiene el tipo de usuario (cliente, dueno, empleado, admin) de la sesión.
    tipo_usuario = session.get('tipo_tabla')

    # Se crea un cursor para la base de datos.
    cursor = mysql.connection.cursor()
    try:
        # Se inserta un nuevo registro en la tabla favoritos con el usuario, tipo y producto.
        cursor.execute(
            "INSERT INTO favoritos (usuario_id, tipo_usuario, producto_id) VALUES (%s, %s, %s)",
            (usuario_id, tipo_usuario, producto_id)
        )
        # Se confirma la transacción.
        mysql.connection.commit()
        # Se cierra el cursor.
        cursor.close()
        # Se retorna éxito.
        return jsonify({'success': True})
    except MySQLdb.IntegrityError as e:
        # Si ocurre un error de integridad (ej. duplicado), se deshace la transacción.
        mysql.connection.rollback()
        cursor.close()
        # Se verifica si el error es por entrada duplicada.
        if "Duplicate entry" in str(e):
            # Si ya existe, se retorna un error indicando que ya está en favoritos.
            return jsonify({'error': 'Ya existe'}), 400
        # Para otros errores de integridad, se retorna un mensaje genérico.
        return jsonify({'error': str(e)}), 500

# ========================================================================
# RUTA: '/api/favoritos/eliminar/<int:producto_id>' (DELETE)
# ========================================================================
# DESCRIPCIÓN: ELIMINA UN PRODUCTO DE FAVORITOS PARA EL USUARIO Y SU ROL.
# ========================================================================

@app.route('/api/favoritos/eliminar/<int:producto_id>', methods=['DELETE'])
@login_required
def api_favoritos_eliminar(producto_id):
    # Se crea un cursor para la base de datos.
    cursor = mysql.connection.cursor()
    # Se ejecuta una sentencia DELETE para eliminar el registro de favoritos
    # que coincida con el usuario_id, tipo_usuario y producto_id.
    cursor.execute(
        "DELETE FROM favoritos WHERE usuario_id=%s AND tipo_usuario=%s AND producto_id=%s",
        (session['usuario_id'], session.get('tipo_tabla'), producto_id)
    )
    # Se confirma la eliminación.
    mysql.connection.commit()
    # Se cierra el cursor.
    cursor.close()
    # Se retorna éxito.
    return jsonify({'success': True})

# ========================================================================
# RUTA: '/todos-productos'
# ========================================================================
# DESCRIPCIÓN: MUESTRA TODOS LOS PRODUCTOS AGRUPADOS POR LOCAL.
# ========================================================================

@app.route('/todos-productos')
def todos_productos():
    cursor = mysql.connection.cursor()
    # Consulta todos los productos con datos del local.
    cursor.execute("""
        SELECT p.id, p.nombre, p.precio, p.stock, l.id as local_id, l.nombre as local_nombre, l.categoria
        FROM productos p
        JOIN locales l ON p.local_id = l.id
        ORDER BY l.nombre, p.nombre
    """)

    rows = cursor.fetchall()
    cursor.close()

    # Lista para agrupar por local.
    grupos = []
    local_actual = None
    local_nombre_actual = None
    categoria_actual = None
    productos_local = []

    for row in rows:
        producto_id = row[0]
        tiene_img = tiene_imagen('producto', producto_id)
        imagen_url = f"/imagen/producto/{producto_id}" if tiene_img else None

        producto = {
            'id': producto_id,
            'nombre': row[1],
            'precio': float(row[2]),
            'stock': row[3],
            'imagen_url': imagen_url
        }

        local_id = row[4]

        # Si cambia de local, guarda el anterior y empieza uno nuevo.
        if local_actual != local_id:
            if local_actual is not None:
                grupos.append({
                    'local_id': local_actual,
                    'local_nombre': local_nombre_actual,
                    'categoria': categoria_actual,
                    'productos': productos_local
                })

            local_actual = local_id
            local_nombre_actual = row[5]
            categoria_actual = row[6]
            productos_local = []

        productos_local.append(producto)

    # Agrega el último grupo.
    if local_actual is not None:
        grupos.append({
            'local_id': local_actual,
            'local_nombre': local_nombre_actual,
            'categoria': categoria_actual,
            'productos': productos_local
        })

    return render_template('todos_productos.html', grupos=grupos)

# ========================================================================
# RUTA: '/local/<codigo>'
# ========================================================================
# DESCRIPCIÓN: PÁGINA PÚBLICA DE UN LOCAL ESPECÍFICO POR SU CÓDIGO.
# INCLUYE INFORMACIÓN DEL LOCAL, DUEÑO, PRODUCTOS Y GALERÍA MULTIMEDIA.
# ========================================================================

@app.route('/local/<codigo>')
def ver_local(codigo):
    # Se crea un cursor para ejecutar consultas SQL.
    cursor = mysql.connection.cursor()
    
    # ====================================================================
    # 1. OBTENER DATOS DEL LOCAL
    # ====================================================================
    # Se consulta la tabla 'locales' usando el código recibido en la URL.
    cursor.execute("""
        SELECT id, nombre, descripcion, ubicacion, categoria, dueno_id, dias_stock,
            anuncios, ofertas, imagen_fondo
        FROM locales WHERE codigo = %s
    """, (codigo,))
    # fetchone() devuelve una sola fila (el local) o None si no existe.
    local = cursor.fetchone()

    # Si no se encuentra el local, se retorna un error 404 con un mensaje.
    if not local:
        return "Local no encontrado", 404

    # ====================================================================
    # 2. ASIGNAR VALORES POR DEFECTO A CAMPOS QUE PUEDEN SER NULL
    # ====================================================================
    # Si algún campo es NULL en la base de datos, se asigna un texto por defecto.
    anuncios = local[7] if local[7] is not None else 'Próximamente más noticias.'
    ofertas = local[8] if local[8] is not None else 'Pronto nuevas promociones.'
    imagen_fondo = local[9] if local[9] is not None else 'static/img/fondos/berries.png'

    # Se extrae el ID del local (primera columna) para usarlo en consultas posteriores.
    local_id = local[0]
    
    # ====================================================================
    # 3. CONSTRUIR DICCIONARIO CON DATOS DEL LOCAL
    # ====================================================================
    # Se prepara un diccionario con toda la información del local.
    # 'imagen_url' se genera usando la función 'tiene_imagen' que verifica si
    # existe una imagen en MongoDB para este local.
    local_data = {
        'id': local_id,
        'nombre': local[1],
        'descripcion': local[2],
        'ubicacion': local[3],
        'categoria': local[4],
        'dueno_id': local[5],
        'dias_stock': local[6],
        'anuncios': anuncios,
        'ofertas': ofertas,
        'imagen_fondo': imagen_fondo,
        'imagen_url': f"/imagen/local/{local_id}" if tiene_imagen('local', local_id) else None
    }

    # ====================================================================
    # 4. OBTENER DATOS DEL DUEÑO
    # ====================================================================
    # Se consulta la tabla 'duenos' usando el 'dueno_id' del local.
    cursor.execute("SELECT nombre, correo, telefono, documento_identidad FROM duenos WHERE id=%s", (local_data['dueno_id'],))
    dueno = cursor.fetchone()
    # Se construye un diccionario con los datos del dueño, o valores por defecto si no existe.
    dueno_data = {
        'nombre': dueno[0] if dueno else "Desconocido",
        'correo': dueno[1] if dueno else "",
        'telefono': dueno[2] if dueno else "",
        'documento': dueno[3] if dueno else ""
    }

    # ====================================================================
    # 5. OBTENER PRODUCTOS DEL LOCAL (CON CORRECCIÓN)
    # ====================================================================
    # Se consultan todos los productos que pertenecen a este local, ordenados por nombre.
    cursor.execute("SELECT id, nombre, precio, stock FROM productos WHERE local_id=%s ORDER BY nombre", (local_id,))
    # Se inicializa una lista vacía para almacenar los productos procesados.
    productos = []
    # Se itera sobre cada fila devuelta por la consulta.
    for row in cursor.fetchall():
        # row[0] es el ID del producto.
        producto_id = row[0]
        
        # ================================================================
        # 5.1 DETERMINAR ESTADO DEL PRODUCTO SEGÚN SU STOCK
        # ================================================================
        # Si el stock es menor o igual a 0, el estado es 'agotado'.
        if row[3] <= 0:
            estado = "agotado"
        # Si el stock es menor a 5, se marca como 'por llegar' (stock bajo).
        elif row[3] < 5:
            estado = "por llegar"
        # En cualquier otro caso, el producto está 'disponible'.
        else:
            estado = "disponible"

        # ================================================================
        # 5.2 VERIFICAR SI EL PRODUCTO TIENE IMAGEN EN MONGODB
        # ================================================================
        # Se usa la función 'tiene_imagen' con la colección 'producto' y el ID del producto.
        tiene_img = tiene_imagen('producto', producto_id)
        
        # ================================================================
        # 5.3 CONSTRUIR DICCIONARIO DEL PRODUCTO (CON PRECIO NUMÉRICO)
        # ================================================================
        # Se agrega el campo 'precio_num' que contiene el precio como número (float),
        # para usarlo en los atributos data-* de la plantilla sin necesidad de filtros.
        productos.append({
            'id': producto_id,
            'nombre': row[1],
            'precio': f"${float(row[2]):.2f}",        # Precio formateado con $ y 2 decimales para mostrar.
            'precio_num': float(row[2]),               # Precio como número puro (para data-precio-raw).
            'stock': row[3],
            'estado': estado,
            'imagen_url': f"/imagen/producto/{producto_id}" if tiene_img else None
        })

    # Se cierra el cursor para liberar la conexión a la base de datos.
    cursor.close()

    # ====================================================================
    # 6. OBTENER ARCHIVOS MULTIMEDIA ASOCIADOS A ESTE LOCAL
    # ====================================================================
    # La función 'listar_multimedia' retorna una lista de metadatos de archivos
    # (fotos, videos, audios) almacenados en GridFS (MongoDB) para este local.
    multimedia = listar_multimedia(local_id)

    # ====================================================================
    # 7. RENDERIZAR LA PLANTILLA CON TODOS LOS DATOS
    # ====================================================================
    # Se pasa a la plantilla 'local.html' el local, el dueño, los productos,
    # el código y la lista multimedia.
    return render_template('local.html',
                        local=local_data,
                        dueno=dueno_data,
                        productos=productos,
                        codigo=codigo,
                        multimedia=multimedia)

# ========================================================================
# RUTA: '/feedback' (GET Y POST)
# ========================================================================
# DESCRIPCIÓN: PERMITE A CUALQUIER USUARIO AUTENTICADO ENVIAR FEEDBACK.
# CORREGIDO PARA QUE USUARIOS DE CUALQUIER ROL (CLIENTE, DUEÑO, EMPLEADO,
# ADMIN) PUEDAN ENVIAR FEEDBACK SIN NECESIDAD DE TENER UN REGISTRO EN
# LA TABLA `usuarios`. SE UTILIZA UN USUARIO SISTEMA DEDICADO PARA EL
# FEEDBACK DE ROLES QUE NO SON CLIENTES.
# ========================================================================

# ========================================================================
# FUNCIÓN AUXILIAR: obtener_o_crear_usuario_sistema
# ========================================================================
# DESCRIPCIÓN: OBTIENE O CREA UN USUARIO SISTEMA DEDICADO PARA FEEDBACK.
# ESTE USUARIO SE USA CUANDO EL USUARIO AUTENTICADO NO ES CLIENTE
# (DUEÑO, EMPLEADO, ADMIN) PARA EVITAR EL ERROR DE CLAVE FORÁNEA.
# RETORNA EL ID DEL USUARIO SISTEMA.
# ========================================================================

def obtener_o_crear_usuario_sistema():
    # Crea un cursor para la base de datos.
    cursor = mysql.connection.cursor()
    # Correo específico para el usuario sistema de feedback.
    correo_sistema = 'sistema@feedback.blooma'

    # Busca si ya existe un usuario con ese correo.
    cursor.execute("SELECT id FROM usuarios WHERE correo = %s", (correo_sistema,))
    fila = cursor.fetchone()

    if fila:
        # Si existe, retorna su ID.
        usuario_id = fila[0]
        cursor.close()
        return usuario_id

    # Si no existe, lo crea.
    cursor.execute("""
        INSERT INTO usuarios (nombre, correo, password, fecha_nacimiento, telefono, direccion, documento_identidad, estado)
        VALUES (%s, %s, %s, '2000-01-01', '0000000000', 'Sistema', 'SISTEMA', 'activo')
    """, ('Sistema Feedback', correo_sistema, 'sistema_feedback_12345'))
    # Se usa una contraseña simple porque este usuario no se usa para iniciar sesión.

    mysql.connection.commit()
    # Obtiene el ID del usuario recién creado.
    usuario_id = cursor.lastrowid
    cursor.close()
    # Retorna el ID del usuario sistema.
    return usuario_id

# ========================================================================
# RUTA: '/feedback' (GET Y POST)
# ========================================================================
@app.route('/feedback', methods=['GET', 'POST'])
@login_required
def feedback():
    # Inicializa las variables para mensajes de error o éxito.
    error = None
    exito = None

    # Si la solicitud es POST (el usuario envió el formulario).
    if request.method == 'POST':
        # Obtiene el mensaje del formulario y elimina espacios al inicio/final.
        mensaje = request.form.get('mensaje', '').strip()

        # Si el mensaje está vacío, muestra un error.
        if not mensaje:
            error = "El mensaje no puede estar vacío"
        else:
            # Obtiene el tipo de tabla y el ID del usuario desde la sesión.
            tipo_tabla = session.get('tipo_tabla')
            usuario_id_sesion = session['usuario_id']
            correo_usuario = None
            nombre_usuario = None

            # ======= CASO: CLIENTE =======
            if tipo_tabla == 'cliente':
                # Busca el correo y nombre en la tabla usuarios.
                cursor = mysql.connection.cursor()
                cursor.execute("SELECT correo, nombre FROM usuarios WHERE id = %s", (usuario_id_sesion,))
                row = cursor.fetchone()
                if row:
                    correo_usuario, nombre_usuario = row
                cursor.close()

            # ======= CASO: DUEÑO =======
            elif tipo_tabla == 'dueno':
                # Busca el correo y nombre en la tabla duenos.
                cursor = mysql.connection.cursor()
                cursor.execute("SELECT correo, nombre FROM duenos WHERE id = %s", (usuario_id_sesion,))
                row = cursor.fetchone()
                if row:
                    correo_usuario, nombre_usuario = row
                cursor.close()

            # ======= CASO: EMPLEADO =======
            elif tipo_tabla == 'empleado':
                # Busca el correo y nombre en la tabla empleados.
                cursor = mysql.connection.cursor()
                cursor.execute("SELECT correo, nombre FROM empleados WHERE id = %s", (usuario_id_sesion,))
                row = cursor.fetchone()
                if row:
                    correo_usuario, nombre_usuario = row
                cursor.close()

            # ======= CASO: ADMINISTRADOR =======
            elif tipo_tabla == 'admin':
                # Busca el correo y nombre en la tabla administradores.
                cursor = mysql.connection.cursor()
                cursor.execute("SELECT correo, nombre FROM administradores WHERE id = %s", (usuario_id_sesion,))
                row = cursor.fetchone()
                if row:
                    correo_usuario, nombre_usuario = row
                cursor.close()

            # Si no se pudo obtener el correo, muestra un error.
            if not correo_usuario:
                error = "No se pudo identificar tu correo."
                return render_template('feedback.html', error=error, exito=exito)

            # ======= OBTENER O CREAR EL USUARIO SISTEMA =======
            # Si el usuario es cliente, se busca su ID en la tabla usuarios.
            if tipo_tabla == 'cliente':
                cursor = mysql.connection.cursor()
                cursor.execute("SELECT id FROM usuarios WHERE correo = %s", (correo_usuario,))
                fila = cursor.fetchone()
                if fila:
                    usuario_id = fila[0]
                else:
                    # Si por alguna razón no se encuentra, se usa el sistema.
                    usuario_id = obtener_o_crear_usuario_sistema()
                cursor.close()
            else:
                # Para roles que no son clientes (dueno, empleado, admin),
                # se usa el usuario sistema dedicado para feedback.
                usuario_id = obtener_o_crear_usuario_sistema()
                # Se actualiza el nombre para identificar quién envió el feedback.
                nombre_usuario = f"{nombre_usuario} ({tipo_tabla})"

            # ======= INSERTAR EL FEEDBACK =======
            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO feedback (usuario_id, mensaje) VALUES (%s, %s)", (usuario_id, mensaje))
            mysql.connection.commit()
            cursor.close()

            # ======= ENVIAR CORREO DE NOTIFICACIÓN =======
            try:
                # Crea un mensaje de correo.
                msg = Message(
                    subject=f"Nuevo feedback de {nombre_usuario or 'Usuario'}",
                    recipients=['blooma.xoko@gmail.com'],
                    body=f"""
                    Usuario: {nombre_usuario or 'Usuario'} (ID: {usuario_id})
                    Correo: {correo_usuario}
                    Fecha: {time.strftime('%Y-%m-%d %H:%M:%S')}
                    Mensaje:
                    {mensaje}
                    """
                )
                # Envía el correo.
                mail.send(msg)
                # Mensaje de éxito.
                exito = "¡Gracias! Tu opinión ha sido enviada."
            except Exception as e:
                # Si falla el envío del correo, igualmente el feedback se guardó.
                exito = "Mensaje guardado correctamente (problema con el correo, pero lo revisaremos)."
                # Imprime el error en la consola para depuración.
                print(f"Error al enviar email: {e}")

    # Renderiza la plantilla feedback.html con los mensajes correspondientes.
    return render_template('feedback.html', error=error, exito=exito)

# ========================================================================
# RUTA: '/api/admin/user/<int:id>/foto' (POST)
# ========================================================================
# DESCRIPCIÓN: ADMIN SUBE FOTO DE PERFIL PARA UN USUARIO.
# ========================================================================

@app.route('/api/admin/user/<int:id>/foto', methods=['POST'])
@login_required
@rol_requerido(['admin'])
def admin_update_user_foto(id):
    if 'foto' not in request.files:
        return jsonify({'error': 'No se envió foto'}), 400

    file = request.files['foto']
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"admin_user_{id}_{int(time.time())}.{ext}")
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        db_path = f"uploads/perfiles/{filename}"

        cursor = mysql.connection.cursor()
        # Busca en usuarios (clientes).
        cursor.execute("SELECT id FROM usuarios WHERE id=%s", (id,))
        if cursor.fetchone():
            cursor.execute("UPDATE usuarios SET foto_perfil=%s WHERE id=%s", (db_path, id))
        else:
            # Busca en duenos.
            cursor.execute("SELECT id FROM duenos WHERE id=%s", (id,))
            if cursor.fetchone():
                cursor.execute("UPDATE duenos SET foto_perfil=%s WHERE id=%s", (db_path, id))
            else:
                # Busca en empleados.
                cursor.execute("UPDATE empleados SET foto_perfil=%s WHERE id=%s", (db_path, id))

        mysql.connection.commit()
        cursor.close()
        return jsonify({'success': True, 'foto_url': db_path})

    return jsonify({'error': 'Formato no permitido'}), 400

# ========================================================================
# RUTA: '/empleado/dashboard'
# ========================================================================
# DESCRIPCIÓN: PANEL DE CONTROL DEL EMPLEADO.
# ========================================================================

@app.route('/empleado/dashboard')
@login_required
@rol_requerido(['empleado'])
def dashboard_empleado():
    empleado_id = session['usuario_id']
    cursor = mysql.connection.cursor()
    cursor.execute("""
        SELECT e.local_id, l.id, l.codigo, l.nombre, l.descripcion, l.ubicacion, l.categoria, l.dias_stock
        FROM empleados e
        JOIN locales l ON e.local_id = l.id
        WHERE e.id = %s
    """, (empleado_id,))
    local = cursor.fetchone()
    cursor.close()

    if not local:
        flash('No tienes un local asignado. Contacta al administrador.', 'danger')
        return redirect('/inicio')

    local_data = {
        'id': local[1],
        'codigo': local[2],
        'nombre': local[3],
        'descripcion': local[4],
        'ubicacion': local[5],
        'categoria': local[6],
        'dias_stock': local[7],
        'imagen_local_url': f"/imagen/local/{local[1]}" if tiene_imagen('local', local[1]) else None
    }

    return render_template('empleado_dashboard.html', local=local_data)

# ========================================================================
# BLOQUE: INICIO DE LA APLICACIÓN
# ========================================================================
# DESCRIPCIÓN: SI EL SCRIPT SE EJECUTA DIRECTAMENTE, INICIA EL SERVIDOR
# FLASK EN MODO DEBUG. ESTO PERMITE PRUEBAS Y DESARROLLO CON RECARGA
# AUTOMÁTICA ANTE CAMBIOS EN EL CÓDIGO.
# ========================================================================

if __name__ == '__main__':
    # Si el script se ejecuta directamente (no importado como módulo),
    # inicia el servidor Flask.
    # debug=True activa el modo de depuración (recarga automática y
    # consola de errores interactiva).
    app.run(debug=True)
