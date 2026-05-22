import pymysql
pymysql.install_as_MySQLdb()

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
import os
import random
import requests
app = Flask(__name__)
app.secret_key = "clave_secreta_open_library"

# ---------------- MYSQL ----------------
app.config['MYSQL_HOST'] = os.getenv('MYSQLHOST')
app.config['MYSQL_USER'] = os.getenv('MYSQLUSER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQLPASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQLDATABASE')
app.config['MYSQL_PORT'] = int(os.getenv('MYSQLPORT', 3306))

mysql = MySQL(app)
# ---------------- CORREO BREVO API ----------------

CORREO_ADMIN = "virtualbiblioteca006@gmail.com"


def enviar_correo(destinatario, asunto, contenido):
    url = "https://api.brevo.com/v3/smtp/email"

    api_key = os.getenv("BREVO_API_KEY")

    if not api_key:
        print("ERROR BREVO: falta la variable BREVO_API_KEY en Railway")
        return False

    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json"
    }

    data = {
        "sender": {
            "name": "MY BIBLIOTECA",
            "email": CORREO_ADMIN
        },
        "to": [
            {
                "email": destinatario
            }
        ],
        "subject": asunto,
        "textContent": contenido
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=15
        )

        print("BREVO STATUS:", response.status_code)
        print("BREVO RESPUESTA:", response.text)

        return response.status_code in [200, 201, 202]

    except Exception as e:
        print("ERROR ENVIANDO CORREO POR BREVO API:", e)
        return False

@app.route("/")
def index():
    if "usuario" in session:
        return redirect(url_for("inicio"))

    if "admin" in session:
        return redirect(url_for("admin_panel"))

    return redirect(url_for("login"))


# ---------------- ADMIN LOGIN ----------------

@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        password = request.form.get("password", "").strip()

        if not usuario or not password:
            flash("Usuario y contraseña son obligatorios")
            return redirect(url_for("admin_login"))

        if usuario == "admin" and password == "12345":
            session.clear()
            session["admin"] = True
            session["admin_nombre"] = "Administrador"
            flash("Bienvenido administrador")
            return redirect(url_for("admin_panel"))
        else:
            flash("Usuario o contraseña de administrador incorrectos")

    return render_template("admin_login.html")


# ---------------- ADMIN PANEL ----------------

@app.route("/admin_panel")
def admin_panel():

    if "admin" not in session:
        flash("Debes iniciar sesión como administrador")
        return redirect(url_for("admin_login"))

    cur = mysql.connection.cursor()

    # TOTAL USUARIOS

    cur.execute("SELECT COUNT(*) FROM usuarios")
    total_usuarios = cur.fetchone()[0] or 0

    # TOTAL TÍTULOS

    cur.execute("SELECT COUNT(*) FROM libros")
    total_titulos = cur.fetchone()[0] or 0

    # TOTAL LIBROS

    cur.execute("SELECT SUM(total) FROM libros")
    total_libros = cur.fetchone()[0] or 0

    # TOTAL PRESTADOS

    cur.execute("SELECT SUM(prestados) FROM libros")
    total_prestados = cur.fetchone()[0] or 0

    # DISPONIBLES

    disponibles = total_libros - total_prestados

    # GANANCIAS

    cur.execute("""
        SELECT SUM(l.precio_prestamo)
        FROM prestamos p
        INNER JOIN libros l ON p.libro_id = l.id
        WHERE p.estado IN (
            'enviado',
            'prestado',
            'devuelto'
        )
    """)

    total_ganado = cur.fetchone()[0] or 0

    # SOLICITUDES

    cur.execute("""
        SELECT
            p.id,
            l.titulo,
            u.usuario,
            u.correo,
            p.nombre_persona,
            p.estado,

            CASE
                WHEN p.estado = 'enviado'
                THEN p.fecha_envio

                ELSE p.fecha_prestamo
            END,

            p.fecha_devolucion,

            l.precio_prestamo

        FROM prestamos p

        INNER JOIN libros l
            ON p.libro_id = l.id

        INNER JOIN usuarios u
            ON p.usuario_id = u.id

        ORDER BY p.id DESC
    """)

    solicitudes = cur.fetchall()

    cur.close()

    return render_template(
        "admin_panel.html",
        total_usuarios=total_usuarios,
        total_titulos=total_titulos,
        total_libros=total_libros,
        total_prestados=total_prestados,
        disponibles=disponibles,
        total_ganado=total_ganado,
        solicitudes=solicitudes
    )

@app.route("/admin_logout")
def admin_logout():
    session.clear()
    flash("Sesión de administrador cerrada")
    return redirect(url_for("admin_login"))


# ---------------- ADMIN USUARIOS ----------------

@app.route("/admin_usuarios")
def admin_usuarios():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, usuario, correo
        FROM usuarios
        ORDER BY id DESC
    """)
    usuarios = cur.fetchall()
    cur.close()

    return render_template("admin_usuarios.html", usuarios=usuarios)


@app.route("/admin_crear_usuario", methods=["POST"])
def admin_crear_usuario():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    usuario = request.form.get("usuario", "").strip()
    correo = request.form.get("correo", "").strip()
    password_plano = request.form.get("password", "").strip()

    if not usuario or not correo or not password_plano:
        flash("Todos los campos son obligatorios")
        return redirect(url_for("admin_usuarios"))

    if len(password_plano) < 6:
        flash("La contraseña debe tener mínimo 6 caracteres")
        return redirect(url_for("admin_usuarios"))

    password = generate_password_hash(password_plano)

    cur = mysql.connection.cursor()

    cur.execute("SELECT id FROM usuarios WHERE correo = %s", (correo,))
    existe = cur.fetchone()

    if existe:
        cur.close()
        flash("Ese correo ya está registrado")
        return redirect(url_for("admin_usuarios"))

    cur.execute("""
        INSERT INTO usuarios (usuario, correo, password)
        VALUES (%s, %s, %s)
    """, (usuario, correo, password))

    mysql.connection.commit()
    cur.close()

    flash("Usuario creado correctamente")
    return redirect(url_for("admin_usuarios"))


@app.route("/editar_usuario/<int:id>", methods=["GET", "POST"])
def editar_usuario(id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    cur = mysql.connection.cursor()

    if request.method == "POST":
        usuario = request.form.get("usuario", "").strip()
        correo = request.form.get("correo", "").strip()
        password_plano = request.form.get("password", "").strip()

        if not usuario or not correo:
            cur.close()
            flash("El usuario y el correo son obligatorios")
            return redirect(url_for("editar_usuario", id=id))

        if password_plano:
            if len(password_plano) < 6:
                cur.close()
                flash("La contraseña debe tener mínimo 6 caracteres")
                return redirect(url_for("editar_usuario", id=id))

            password = generate_password_hash(password_plano)

            cur.execute("""
                UPDATE usuarios
                SET usuario = %s, correo = %s, password = %s
                WHERE id = %s
            """, (usuario, correo, password, id))
        else:
            cur.execute("""
                UPDATE usuarios
                SET usuario = %s, correo = %s
                WHERE id = %s
            """, (usuario, correo, id))

        mysql.connection.commit()
        cur.close()

        flash("Usuario editado correctamente")
        return redirect(url_for("admin_usuarios"))

    cur.execute("""
        SELECT id, usuario, correo
        FROM usuarios
        WHERE id = %s
    """, (id,))
    usuario = cur.fetchone()
    cur.close()

    if not usuario:
        flash("Usuario no encontrado")
        return redirect(url_for("admin_usuarios"))

    return render_template("editar_usuario.html", usuario=usuario)


@app.route("/eliminar_usuario/<int:id>", methods=["POST"])
def eliminar_usuario(id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM prestamos WHERE usuario_id = %s", (id,))
    cur.execute("DELETE FROM usuarios WHERE id = %s", (id,))

    mysql.connection.commit()
    cur.close()

    flash("Usuario eliminado correctamente")
    return redirect(url_for("admin_usuarios"))


# ---------------- ADMIN LIBROS ----------------

@app.route("/admin_libros")
def admin_libros():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT id, titulo, autor, categoria, total, prestados, imagen, pdf, precio_prestamo
        FROM libros
        ORDER BY id DESC
    """)
    libros = cur.fetchall()
    cur.close()

    return render_template("admin_libros.html", libros=libros)


@app.route("/admin_crear_libro", methods=["POST"])
def admin_crear_libro():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    titulo = request.form.get("titulo", "").strip()
    autor = request.form.get("autor", "").strip()
    categoria = request.form.get("categoria", "").strip()
    total = request.form.get("total", "").strip()
    imagen = request.form.get("imagen", "").strip()
    pdf = request.form.get("pdf", "").strip()
    precio_prestamo = request.form.get("precio_prestamo", "").strip()

    if not titulo or not autor or not categoria or not total or not precio_prestamo:
        flash("Todos los campos obligatorios del libro deben estar completos")
        return redirect(url_for("admin_libros"))

    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO libros
        (titulo, autor, categoria, total, prestados, imagen, pdf, precio_prestamo)
        VALUES (%s, %s, %s, %s, 0, %s, %s, %s)
    """, (titulo, autor, categoria, total, imagen, pdf, precio_prestamo))

    mysql.connection.commit()
    cur.close()

    flash("Libro creado correctamente")
    return redirect(url_for("admin_libros"))


@app.route("/editar_libro/<int:id>", methods=["GET", "POST"])
def editar_libro(id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    cur = mysql.connection.cursor()

    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        autor = request.form.get("autor", "").strip()
        categoria = request.form.get("categoria", "").strip()
        total = request.form.get("total", "").strip()
        imagen = request.form.get("imagen", "").strip()
        pdf = request.form.get("pdf", "").strip()
        precio_prestamo = request.form.get("precio_prestamo", "").strip()

        if not titulo or not autor or not categoria or not total or not precio_prestamo:
            cur.close()
            flash("Todos los campos obligatorios deben estar completos")
            return redirect(url_for("editar_libro", id=id))

        cur.execute("""
            UPDATE libros
            SET titulo = %s,
                autor = %s,
                categoria = %s,
                total = %s,
                imagen = %s,
                pdf = %s,
                precio_prestamo = %s
            WHERE id = %s
        """, (titulo, autor, categoria, total, imagen, pdf, precio_prestamo, id))

        mysql.connection.commit()
        cur.close()

        flash("Libro editado correctamente")
        return redirect(url_for("admin_libros"))

    cur.execute("""
        SELECT id, titulo, autor, categoria, total, prestados, imagen, pdf, precio_prestamo
        FROM libros
        WHERE id = %s
    """, (id,))
    libro = cur.fetchone()
    cur.close()

    if not libro:
        flash("Libro no encontrado")
        return redirect(url_for("admin_libros"))

    return render_template("editar_libro.html", libro=libro)


@app.route("/eliminar_libro/<int:id>", methods=["POST"])
def eliminar_libro(id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    cur = mysql.connection.cursor()

    cur.execute("DELETE FROM prestamos WHERE libro_id = %s", (id,))
    cur.execute("DELETE FROM libros WHERE id = %s", (id,))

    mysql.connection.commit()
    cur.close()

    flash("Libro eliminado correctamente")
    return redirect(url_for("admin_libros"))


# ---------------- ADMIN SOLICITUDES ----------------

@app.route("/admin_solicitudes")
def admin_solicitudes():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT 
            p.id,
            l.titulo,
            u.usuario,
            u.correo,
            p.nombre_persona,
            p.celular,
            p.direccion,
            p.estado,
            p.fecha_solicitud,
            l.precio_prestamo
        FROM prestamos p
        INNER JOIN libros l ON p.libro_id = l.id
        INNER JOIN usuarios u ON p.usuario_id = u.id
        WHERE p.estado IN ('solicitado', 'enviado', 'devolucion_solicitada', 'recogida')
        ORDER BY p.id DESC
    """)
    solicitudes = cur.fetchall()

    cur.execute("""
        SELECT 
            p.id,
            l.titulo,
            u.usuario,
            u.correo,
            p.nombre_persona,
            p.celular,
            p.direccion,
            p.estado,
            p.fecha_prestamo,
            l.precio_prestamo
        FROM prestamos p
        INNER JOIN libros l ON p.libro_id = l.id
        INNER JOIN usuarios u ON p.usuario_id = u.id
        WHERE p.estado = 'prestado'
        ORDER BY p.fecha_prestamo DESC
    """)
    prestamos_activos = cur.fetchall()

    cur.close()

    return render_template(
        "admin_solicitudes.html",
        solicitudes=solicitudes,
        prestamos_activos=prestamos_activos
    )


@app.route("/admin_enviar_libro/<int:prestamo_id>", methods=["POST"])
def admin_enviar_libro(prestamo_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            p.id,
            p.estado,
            p.nombre_persona,
            p.libro_id,
            l.titulo,
            l.total,
            l.prestados,
            l.precio_prestamo,
            u.correo,
            u.usuario
        FROM prestamos p
        INNER JOIN libros l ON p.libro_id = l.id
        INNER JOIN usuarios u ON p.usuario_id = u.id
        WHERE p.id = %s
    """, (prestamo_id,))
    prestamo = cur.fetchone()

    if not prestamo:
        cur.close()
        flash("No se encontró la solicitud")
        return redirect(url_for("admin_solicitudes"))

    if prestamo[1] not in ("solicitado", "enviado"):
        cur.close()
        flash("Esta solicitud ya no está pendiente")
        return redirect(url_for("admin_solicitudes"))

    if prestamo[6] >= prestamo[5]:
        cur.close()
        flash("No hay unidades disponibles para enviar este libro")
        return redirect(url_for("admin_solicitudes"))

    enlace_entrega = url_for(
        "confirmar_entrega",
        prestamo_id=prestamo_id,
        _external=True
    )

    try:
        asunto = "Verificación de entrega - MY BIBLIOTECA"
        contenido = f"""
Hola {prestamo[2]}.

El administrador ya dio la orden de enviar el libro: {prestamo[4]}.

Valor del préstamo: ${prestamo[7]}

Debes cancelar este valor al domiciliario cuando recibas el libro.

Cuando el libro llegue a tu casa, entra a este enlace para verificar la entrega:

{enlace_entrega}

Después de verificar, el libro quedará marcado como PRESTADO en el sistema.

Gracias por usar MY BIBLIOTECA.
"""
        correo_enviado = enviar_correo(prestamo[8], asunto, contenido)

        if not correo_enviado:
            raise Exception("Brevo no pudo enviar el correo de verificación")

        cur.execute("""
            UPDATE prestamos
            SET estado = 'enviado',
                fecha_envio = NOW()
            WHERE id = %s
        """, (prestamo_id,))
        mysql.connection.commit()
        flash(f"Correo de verificación enviado a {prestamo[8]}")

    except Exception as e:
        print("ERROR ENVIANDO CORREO DE VERIFICACIÓN:", e)
        flash("No se pudo enviar el correo de verificación. Revisa la configuración de Brevo")

    cur.close()
    return redirect(url_for("admin_solicitudes"))


@app.route("/admin_recoger_libro/<int:prestamo_id>", methods=["POST"])
def admin_recoger_libro(prestamo_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT
            p.id,
            p.estado,
            p.nombre_persona,
            p.libro_id,
            l.titulo,
            u.correo,
            u.usuario
        FROM prestamos p
        INNER JOIN libros l ON p.libro_id = l.id
        INNER JOIN usuarios u ON p.usuario_id = u.id
        WHERE p.id = %s
    """, (prestamo_id,))
    prestamo = cur.fetchone()

    if not prestamo:
        cur.close()
        flash("No se encontró la solicitud de devolución")
        return redirect(url_for("admin_solicitudes"))

    if prestamo[1] not in ("devolucion_solicitada", "recogida"):
        cur.close()
        flash("Esta devolución no está pendiente")
        return redirect(url_for("admin_solicitudes"))

    enlace_devolucion = url_for(
        "confirmar_devolucion",
        prestamo_id=prestamo_id,
        _external=True
    )

    try:
        asunto = "Verificación de devolución - MY BIBLIOTECA"
        contenido = f"""
Hola {prestamo[2]}.

El administrador ya dio la orden de recoger el libro: {prestamo[4]}.

Cuando ya hayas entregado el libro, confirma aquí:

{enlace_devolucion}

Después de confirmar, el libro quedará devuelto y disponible en el sistema.

Gracias por usar MY BIBLIOTECA.
"""
        correo_enviado = enviar_correo(prestamo[5], asunto, contenido)

        if not correo_enviado:
            raise Exception("Brevo no pudo enviar el correo de devolución")

        cur.execute("""
            UPDATE prestamos
            SET estado = 'recogida'
            WHERE id = %s
        """, (prestamo_id,))

        mysql.connection.commit()
        flash(f"Correo de verificación de devolución enviado a {prestamo[5]}")

    except Exception as e:
        print("ERROR ENVIANDO CORREO DE DEVOLUCIÓN:", e)
        flash("No se pudo enviar el correo de devolución")

    cur.close()
    return redirect(url_for("admin_solicitudes"))


# ---------------- REGISTRO USUARIO ----------------

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":

        usuario = request.form.get("usuario", "").strip()
        correo = request.form.get("correo", "").strip()
        celular = request.form.get("celular", "").strip()
        password_plano = request.form.get("password", "").strip()
        confirmar_password = request.form.get("confirmar_password", "").strip()

        datos = {
            "usuario": usuario,
            "correo": correo,
            "celular": celular
        }

        if not usuario or not correo or not celular or not password_plano or not confirmar_password:
            flash("Todos los campos son obligatorios")
            return render_template("registro.html", **datos)

        # VALIDAR SOLO NÚMEROS

        if not celular.isdigit():
            flash("El número de celular solo debe contener dígitos")
            return render_template("registro.html", **datos)

        # VALIDAR EXACTAMENTE 10 DÍGITOS

        if len(celular) != 10:
            flash("El número de celular debe tener exactamente 10 dígitos")
            return render_template("registro.html", **datos)

        # VALIDAR CONTRASEÑA

        if len(password_plano) < 6:
            flash("La contraseña debe tener mínimo 6 caracteres")
            return render_template("registro.html", **datos)

        # VALIDAR CONFIRMACIÓN

        if password_plano != confirmar_password:
            flash("Las contraseñas no coinciden")
            return render_template("registro.html", **datos)

        cur = mysql.connection.cursor()

        # VALIDAR CORREO REPETIDO

        cur.execute("""
            SELECT id
            FROM usuarios
            WHERE correo = %s
        """, (correo,))

        existe_correo = cur.fetchone()

        if existe_correo:
            cur.close()
            flash("Ese correo ya está registrado")
            return render_template("registro.html", **datos)

        # VALIDAR USUARIO REPETIDO

        cur = mysql.connection.cursor()

        cur.execute("""
            SELECT id
            FROM usuarios
            WHERE usuario = %s
        """, (usuario,))

        existe_usuario = cur.fetchone()

        if existe_usuario:
            cur.close()
            flash("Ese nombre de usuario ya está registrado")
            return render_template("registro.html", **datos)

        # VALIDAR CELULAR REPETIDO

        cur = mysql.connection.cursor()

        cur.execute("""
            SELECT id
            FROM usuarios
            WHERE celular = %s
        """, (celular,))

        existe_celular = cur.fetchone()

        if existe_celular:
            cur.close()
            flash("Ese número de celular ya está registrado")
            return render_template("registro.html", **datos)

        # CREAR PASSWORD ENCRIPTADA

        password = generate_password_hash(password_plano)

        # INSERTAR USUARIO

        cur = mysql.connection.cursor()

        cur.execute("""
            INSERT INTO usuarios (
                usuario,
                correo,
                celular,
                password
            )
            VALUES (%s, %s, %s, %s)
        """, (
            usuario,
            correo,
            celular,
            password
        ))

        mysql.connection.commit()
        cur.close()

        flash("Cuenta creada correctamente")

        return redirect(url_for("login"))

    return render_template("registro.html")


# ---------------- LOGIN USUARIO ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form.get("correo", "").strip()
        password = request.form.get("password", "").strip()

        if not correo or not password:
            flash("Correo y contraseña son obligatorios")
            return redirect(url_for("login"))

        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT id, usuario, correo, password
            FROM usuarios
            WHERE correo = %s
        """, (correo,))
        usuario = cur.fetchone()
        cur.close()

        if usuario and check_password_hash(usuario[3], password):
            session.clear()
            session["usuario_id"] = usuario[0]
            session["usuario"] = usuario[1]
            session["correo"] = usuario[2]
            flash("Inicio de sesión correcto")
            return redirect(url_for("inicio"))
        else:
            flash("Correo o contraseña incorrectos")

    return render_template("login.html")


# ---------------- RECUPERAR CONTRASEÑA ----------------

@app.route("/recuperar_password", methods=["GET", "POST"])
def recuperar_password():
    if request.method == "POST":
        correo = request.form.get("correo", "").strip()

        if not correo:
            flash("El correo es obligatorio")
            return redirect(url_for("recuperar_password"))

        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT id, usuario
            FROM usuarios
            WHERE correo = %s
        """, (correo,))
        usuario = cur.fetchone()
        cur.close()

        if not usuario:
            flash("No existe una cuenta con ese correo")
            return redirect(url_for("recuperar_password"))

        codigo = str(random.randint(100000, 999999))

        session["codigo_recuperacion"] = codigo
        session["correo_recuperacion"] = correo

        try:
            asunto = "Código de recuperación - MY BIBLIOTECA"
            contenido = f"""
Hola {usuario[1]}.

Recibimos una solicitud para recuperar tu contraseña.

Tu código de recuperación es:

{codigo}

Ingresa este código en la página de verificación para crear una nueva contraseña.

Si no solicitaste este cambio, ignora este mensaje.

MY BIBLIOTECA
"""

            correo_enviado = enviar_correo(correo, asunto, contenido)

            if not correo_enviado:
                raise Exception("Brevo no pudo enviar el código")

            flash("Te enviamos un código de recuperación al correo")
            return redirect(url_for("verificar_codigo"))

        except Exception as e:
            print("ERROR ENVIANDO CÓDIGO:", e)
            flash("No se pudo enviar el correo. Revisa la configuración de Brevo")
            return redirect(url_for("recuperar_password"))

    return render_template("recuperar_password.html")


# ---------------- VERIFICAR CÓDIGO ----------------

@app.route("/verificar_codigo", methods=["GET", "POST"])
def verificar_codigo():
    if request.method == "POST":
        codigo = request.form.get("codigo", "").strip()
        nueva_password = request.form.get("password", "").strip()
        confirmar_password = request.form.get("confirmar_password", "").strip()

        codigo_guardado = session.get("codigo_recuperacion")
        correo = session.get("correo_recuperacion")

        if not codigo_guardado or not correo:
            flash("Primero debes solicitar un código de recuperación")
            return redirect(url_for("recuperar_password"))

        if not codigo or not nueva_password or not confirmar_password:
            flash("Todos los campos son obligatorios")
            return redirect(url_for("verificar_codigo"))

        if codigo != codigo_guardado:
            flash("Código incorrecto")
            return redirect(url_for("verificar_codigo"))

        if len(nueva_password) < 6:
            flash("La contraseña debe tener mínimo 6 caracteres")
            return redirect(url_for("verificar_codigo"))

        if nueva_password != confirmar_password:
            flash("Las contraseñas no coinciden")
            return redirect(url_for("verificar_codigo"))

        password_hash = generate_password_hash(nueva_password)

        cur = mysql.connection.cursor()
        cur.execute("""
            UPDATE usuarios
            SET password = %s
            WHERE correo = %s
        """, (password_hash, correo))

        mysql.connection.commit()
        cur.close()

        session.pop("codigo_recuperacion", None)
        session.pop("correo_recuperacion", None)

        flash("Contraseña actualizada correctamente. Ya puedes iniciar sesión")
        return redirect(url_for("login"))

    return render_template("verificar_codigo.html")


# ---------------- INICIO USUARIO ----------------

@app.route("/inicio")
def inicio():
    if "usuario" not in session:
        return redirect(url_for("login"))

    buscar = request.args.get("buscar", "")
    categoria = request.args.get("categoria", "")
    estado = request.args.get("estado", "")
    usuario_id = session["usuario_id"]

    cur = mysql.connection.cursor()

    valores = []

    if estado == "prestados":

        query = """
            SELECT 
                l.id,
                l.titulo,
                l.autor,
                l.categoria,
                l.total,
                l.prestados,
                l.imagen,
                l.pdf,
                l.precio_prestamo
            FROM libros l
            INNER JOIN prestamos p
                ON l.id = p.libro_id
            WHERE p.usuario_id = %s
            AND p.estado = 'prestado'
        """

        valores = [usuario_id]

        if buscar:
            query += """
                AND (
                    l.titulo LIKE %s
                    OR l.autor LIKE %s
                    OR l.categoria LIKE %s
                )
            """
            valores.extend([f"%{buscar}%", f"%{buscar}%", f"%{buscar}%"])

        if categoria:
            query += " AND l.categoria = %s"
            valores.append(categoria)

    else:

        query = """
            SELECT id, titulo, autor, categoria, total, prestados, imagen, pdf, precio_prestamo
            FROM libros
            WHERE 1=1
        """

        if buscar:
            query += """
                AND (
                    titulo LIKE %s
                    OR autor LIKE %s
                    OR categoria LIKE %s
                )
            """
            valores.extend([f"%{buscar}%", f"%{buscar}%", f"%{buscar}%"])

        if categoria:
            query += " AND categoria = %s"
            valores.append(categoria)

        if estado == "disponibles":
            query += " AND total > prestados"

    cur.execute(query, valores)
    libros = cur.fetchall()

    cur.execute("""
        SELECT libro_id 
        FROM prestamos
        WHERE usuario_id = %s 
        AND estado = 'prestado'
    """, (usuario_id,))
    libros_prestados_usuario = [fila[0] for fila in cur.fetchall()]

    cur.execute("SELECT SUM(total) FROM libros")
    total_libros = cur.fetchone()[0] or 0

    cur.execute("SELECT SUM(prestados) FROM libros")
    total_prestados = cur.fetchone()[0] or 0

    disponibles = total_libros - total_prestados

    cur.execute("SELECT DISTINCT categoria FROM libros")
    categorias = cur.fetchall()

    cur.close()

    return render_template(
        "inicio.html",
        libros=libros,
        usuario=session["usuario"],
        total_libros=total_libros,
        total_prestados=total_prestados,
        disponibles=disponibles,
        buscar=buscar,
        categoria=categoria,
        categorias=categorias,
        estado=estado,
        libros_prestados_usuario=libros_prestados_usuario
    )

# ---------------- PRESTAR ----------------

@app.route("/prestar/<int:id>", methods=["GET", "POST"])
def prestar(id):

    if "usuario" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT id, titulo, autor, categoria, total, prestados, imagen, pdf, precio_prestamo
        FROM libros
        WHERE id = %s
    """, (id,))

    libro = cur.fetchone()

    if not libro:
        cur.close()
        flash("Libro no encontrado")
        return redirect(url_for("inicio"))

    if libro[5] >= libro[4]:
        cur.close()
        flash("Este libro no está disponible")
        return redirect(url_for("inicio"))

    if request.method == "POST":

        nombre = session["usuario"]
        correo = session["correo"]

        direccion = request.form.get("direccion", "").strip()

        if not direccion:
            cur.close()
            flash("La dirección es obligatoria")
            return redirect(url_for("prestar", id=id))

        cur.execute("""
            SELECT celular
            FROM usuarios
            WHERE id = %s
        """, (usuario_id,))

        usuario_data = cur.fetchone()

        if not usuario_data:
            cur.close()
            flash("Usuario no encontrado")
            return redirect(url_for("login"))

        celular = usuario_data[0]

        cur.execute("""
            SELECT id
            FROM prestamos
            WHERE usuario_id = %s
            AND libro_id = %s
            AND estado IN (
                'solicitado',
                'enviado',
                'prestado',
                'devolucion_solicitada',
                'recogida'
            )
            LIMIT 1
        """, (usuario_id, id))

        existe = cur.fetchone()

        if existe:
            cur.close()
            flash("Ya tienes una solicitud o préstamo activo para este libro")
            return redirect(url_for("inicio"))

        cur.execute("""
            INSERT INTO prestamos
            (
                usuario_id,
                libro_id,
                nombre_persona,
                celular,
                direccion,
                estado,
                fecha_solicitud
            )
            VALUES (%s, %s, %s, %s, %s, 'solicitado', NOW())
        """, (
            usuario_id,
            id,
            nombre,
            celular,
            direccion
        ))

        mysql.connection.commit()

        try:

            asunto = "Nueva solicitud de préstamo"
            contenido = f"""
Nueva solicitud de préstamo.

Nombre: {nombre}
Correo: {correo}
Celular: {celular}
Dirección: {direccion}
Libro solicitado: {libro[1]}

Valor del préstamo: ${libro[8]}

El usuario debe pagar este valor al domiciliario cuando reciba el libro.

Entra al panel de administrador y presiona ENVIAR LIBRO.
"""

            enviar_correo(CORREO_ADMIN, asunto, contenido)

        except Exception as e:
            print("ERROR AVISANDO AL ADMIN:", e)

        cur.close()

        flash(
            f"Usted ha solicitado prestar este libro. "
            f"El valor del préstamo es de ${libro[8]}. "
            f"En unos minutos le llegará un mensaje de verificación al correo {correo}"
        )

        return redirect(url_for("inicio"))

    cur.close()

    return render_template(
        "confirmar_prestamo.html",
        libro=libro,
        correo=session["correo"],
        usuario=session["usuario"]
    )


# ---------------- CONFIRMAR ENTREGA ----------------

@app.route("/confirmar_entrega/<int:prestamo_id>")
def confirmar_entrega(prestamo_id):
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT 
            p.id,
            p.libro_id,
            p.usuario_id,
            p.estado,
            l.titulo,
            l.total,
            l.prestados,
            u.usuario,
            u.correo
        FROM prestamos p
        INNER JOIN libros l ON p.libro_id = l.id
        INNER JOIN usuarios u ON p.usuario_id = u.id
        WHERE p.id = %s
    """, (prestamo_id,))

    prestamo = cur.fetchone()

    if not prestamo:
        cur.close()
        flash("No se encontró este préstamo")
        return redirect(url_for("login"))

    if prestamo[3] != "enviado":
        cur.close()
        flash("Este préstamo todavía no ha sido enviado por el administrador o ya fue confirmado")
        return redirect(url_for("login"))

    if prestamo[6] >= prestamo[5]:
        cur.close()
        flash("Este libro ya no tiene unidades disponibles")
        return redirect(url_for("login"))

    cur.execute("""
        UPDATE prestamos
        SET estado = 'prestado',
            fecha_prestamo = NOW()
        WHERE id = %s
    """, (prestamo_id,))

    cur.execute("""
        UPDATE libros
        SET prestados = prestados + 1
        WHERE id = %s
    """, (prestamo[1],))

    mysql.connection.commit()

    try:
        asunto = "Libro confirmado como entregado"
        contenido = f"""
El usuario confirmó que recibió el libro.

Usuario: {prestamo[7]}
Correo: {prestamo[8]}
Libro: {prestamo[4]}

Ahora aparece como libro prestado.
"""

        enviar_correo(CORREO_ADMIN, asunto, contenido)

    except Exception as e:
        print("ERROR ENVIANDO CORREO AL ADMIN:", e)

    cur.close()

    flash("Entrega confirmada correctamente. Ya puedes devolver el libro.")
    return redirect(url_for("login"))


# ---------------- DEVOLVER ----------------

@app.route("/devolver/<int:id>", methods=["POST"])
def devolver(id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    usuario_id = session["usuario_id"]
    nombre = session["usuario"]
    correo = session["correo"]

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT id, titulo, prestados
        FROM libros
        WHERE id = %s
    """, (id,))
    libro = cur.fetchone()

    if not libro:
        cur.close()
        flash("Libro no encontrado")
        return redirect(url_for("inicio"))

    cur.execute("""
        SELECT id
        FROM prestamos
        WHERE usuario_id = %s
        AND libro_id = %s
        AND estado = 'prestado'
        ORDER BY id DESC
        LIMIT 1
    """, (usuario_id, id))
    prestamo = cur.fetchone()

    if not prestamo:
        cur.close()
        flash("No tienes este libro prestado o ya solicitaste la devolución")
        return redirect(url_for("inicio"))

    cur.execute("""
        UPDATE prestamos
        SET estado = 'devolucion_solicitada'
        WHERE id = %s
    """, (prestamo[0],))

    mysql.connection.commit()

    try:
        asunto = "Nueva solicitud de devolución"
        contenido = f"""
Nueva solicitud de devolución.

Usuario: {nombre}
Correo: {correo}
Libro: {libro[1]}

Entra al panel de administrador y presiona RECOGER LIBRO para enviarle el correo de verificación al cliente.
"""

        enviar_correo(CORREO_ADMIN, asunto, contenido)

    except Exception as e:
        print("ERROR ENVIANDO CORREO AL ADMIN:", e)

    cur.close()

    flash("Solicitaste devolver este libro. El administrador debe recogerlo y enviarte la verificación.")
    return redirect(url_for("inicio"))


# ---------------- CONFIRMAR DEVOLUCIÓN ----------------

@app.route("/confirmar_devolucion/<int:prestamo_id>")
def confirmar_devolucion(prestamo_id):
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT 
            p.id,
            p.libro_id,
            p.usuario_id,
            p.estado,
            l.titulo,
            u.usuario,
            u.correo
        FROM prestamos p
        INNER JOIN libros l ON p.libro_id = l.id
        INNER JOIN usuarios u ON p.usuario_id = u.id
        WHERE p.id = %s
    """, (prestamo_id,))

    prestamo = cur.fetchone()

    if not prestamo:
        cur.close()
        flash("No se encontró esta devolución")
        return redirect(url_for("login"))

    if prestamo[3] != "recogida":
        cur.close()
        flash("Esta devolución todavía no fue autorizada por el administrador o ya fue confirmada")
        return redirect(url_for("login"))

    cur.execute("""
        UPDATE prestamos
        SET estado = 'devuelto',
            fecha_devolucion = NOW()
        WHERE id = %s
    """, (prestamo_id,))

    cur.execute("""
        UPDATE libros
        SET prestados = prestados - 1
        WHERE id = %s AND prestados > 0
    """, (prestamo[1],))

    mysql.connection.commit()

    try:
        asunto = "Libro confirmado como devuelto"
        contenido = f"""
El usuario confirmó que ya entregó el libro.

Usuario: {prestamo[5]}
Correo: {prestamo[6]}
Libro: {prestamo[4]}

El libro ya quedó disponible nuevamente.
"""

        enviar_correo(CORREO_ADMIN, asunto, contenido)

    except Exception as e:
        print("ERROR ENVIANDO CORREO AL ADMIN:", e)

    cur.close()

    flash("Devolución confirmada correctamente. El libro ya quedó disponible.")
    return redirect(url_for("login"))


@app.route("/leer/<archivo>")
def leer_pdf(archivo):
    if "usuario" not in session:
        return redirect(url_for("login"))

    carpeta_pdfs = os.path.join(app.root_path, "static", "pdfs")
    return send_from_directory(carpeta_pdfs, archivo)


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente")
    return redirect(url_for("login"))

@app.route("/admin_ganancias")
def admin_ganancias():

    if "admin" not in session:
        return redirect(url_for("admin_login"))

    cur = mysql.connection.cursor()

    # HISTORIAL DE GANANCIAS

    cur.execute("""
        SELECT
            p.id,
            l.titulo,
            u.usuario,
            l.precio_prestamo,
            p.estado,

            CASE
                WHEN p.estado = 'enviado'
                THEN p.fecha_envio

                ELSE p.fecha_prestamo
            END

        FROM prestamos p

        INNER JOIN libros l
            ON p.libro_id = l.id

        INNER JOIN usuarios u
            ON p.usuario_id = u.id

        WHERE p.estado IN (
            'enviado',
            'prestado',
            'devuelto'
        )

        ORDER BY p.id DESC
    """)

    ganancias = cur.fetchall()

    # TOTAL GANADO

    cur.execute("""
        SELECT SUM(l.precio_prestamo)

        FROM prestamos p

        INNER JOIN libros l
            ON p.libro_id = l.id

        WHERE p.estado IN (
            'enviado',
            'prestado',
            'devuelto'
        )
    """)

    total_ganado = cur.fetchone()[0] or 0

    cur.close()

    return render_template(
        "admin_ganancias.html",
        ganancias=ganancias,
        total_ganado=total_ganado
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
