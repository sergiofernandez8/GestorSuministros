import calendar
import os
from collections import defaultdict
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, flash
from sqlalchemy import extract, func
from werkzeug.utils import secure_filename

from models import Usuario, Venta, Producto, Proveedor
from db import session as db_session
from sqlalchemy.orm import configure_mappers
from werkzeug.security import check_password_hash

# Asegura que SQLAlchemy cargue correctamente los mapeos
configure_mappers()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave_por_defecto")

# 🔧 Añadido para solucionar el KeyError
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images')

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}


@app.route("/")
def home():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = request.form["correo"].strip().lower()
        password = request.form["password"]

        # Mostrar lo que se está introduciendo
        print("Correo introducido:", correo)

        # Busca usuario en bbdd
        usuario = db_session.query(Usuario).filter(Usuario.correo == correo).first()

        if usuario is None:
            flash("Correo no encontrado")
            return render_template("login.html")

        if check_password_hash(usuario.contraseña, password):
            session["user_id"] = usuario.id_usuario
            session["nombre"] = usuario.nombre
            session["rol"] = usuario.rol
            print("Inicio de sesión correcto:", usuario.nombre)
            return redirect(url_for("dashboard"))
        else:
            flash("Correo o contraseña incorrectos")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nombre = request.form["nombre"]
        correo = request.form["correo"].strip().lower()
        password = request.form["password"]

        usuario_existente = db_session.query(Usuario).filter_by(correo=correo).first()
        if usuario_existente:
            flash("Ese correo ya está registrado.")
            return redirect(url_for("register"))

        nuevo_usuario = Usuario(nombre=nombre, correo=correo)
        nuevo_usuario.set_password(password)

        if correo == "admin@admin.com":
            nuevo_usuario.rol = "administrador"
        else:
            nuevo_usuario.rol = "cliente"

        db_session.add(nuevo_usuario)
        db_session.commit()
        flash("Usuario registrado con éxito.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["rol"] == "cliente":
        return redirect(url_for("dashboard_cliente"))
    elif session["rol"] == "administrador":
        return redirect(url_for("dashboard_admin"))
    else:
        flash("Rol no reconocido.")
        return redirect(url_for("login"))


@app.route("/dashboard_admin")
def dashboard_admin():
    if "user_id" not in session or session["rol"] != "administrador":
        return redirect(url_for("login"))

    # Total de ventas
    total_ventas = db_session.query(Venta).count()

    # Beneficio total
    beneficio_total = db_session.query(func.sum(Venta.cantidad * Venta.precio_unitario)).scalar() or 0

    # Ventas por mes
    ventas = db_session.query(Venta).all()
    ingresos_por_mes = defaultdict(float)

    for v in ventas:
        fecha = v.fecha_venta
        if isinstance(fecha, str):
            fecha = datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S")
        mes = fecha.strftime("%B")
        ingresos_por_mes[mes] += v.cantidad * v.precio_unitario

    meses_ordenados = list(calendar.month_name)[1:]
    labels = []
    valores = []

    for mes in meses_ordenados:
        if mes in ingresos_por_mes:
            labels.append(mes)
            valores.append(round(ingresos_por_mes[mes], 2))

    # Productos más vendidos
    productos_mas_vendidos = (
        db_session.query(
            Producto.id_producto,
            Producto.nombre,
            Producto.imagen,
            func.count(Venta.id_venta).label("ventas")
        )
        .join(Venta, Producto.id_producto == Venta.id_producto)
        .group_by(Producto.id_producto)
        .order_by(func.count(Venta.id_venta).desc())
        .limit(5)
        .all()
    )

    # Productos con bajo stock (menos del 10%)
    productos_bajo_stock = []
    todos_productos = db_session.query(Producto).all()
    for producto in todos_productos:
        if producto.cantidad_en_stock <= 0:
            continue

        total_vendido = db_session.query(func.sum(Venta.cantidad)).filter_by(id_producto=producto.id_producto).scalar() or 0
        stock_inicial = producto.cantidad_en_stock + total_vendido
        if stock_inicial == 0:
            continue

        porcentaje_restante = producto.cantidad_en_stock / stock_inicial
        if porcentaje_restante <= 0.1:
            productos_bajo_stock.append(producto)

    return render_template(
        "dashboard_admin.html",
        total_ventas=total_ventas,
        beneficio_total=beneficio_total,
        labels=labels,
        valores=valores,
        productos_mas_vendidos=productos_mas_vendidos,
        productos_bajo_stock=productos_bajo_stock  # 👉 lo pasamos a la plantilla
    )


@app.route("/admin/productos", methods=["GET", "POST"])
def admin_productos():
    if "user_id" not in session or session["rol"] != "administrador":
        return redirect(url_for("login"))

    productos = db_session.query(Producto).all()
    proveedores = db_session.query(Proveedor).all()
    return render_template("admin_productos.html", productos=productos, proveedores=proveedores)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/admin/productos/agregar", methods=["POST"])
def agregar_producto():
    nombre = request.form["nombre"]
    descripcion = request.form["descripcion"]
    cantidad_en_stock = int(request.form["stock"])
    precio = float(request.form["precio"])
    ubicacion = request.form["ubicacion"]
    color = request.form["color"]
    id_proveedor = int(request.form["id_proveedor"])

    # Imagen
    imagen_file = request.files.get("imagen")
    if imagen_file and allowed_file(imagen_file.filename):
        filename = secure_filename(imagen_file.filename)
        imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        imagen_file.save(imagen_path)
    else:
        flash("Imagen no válida o no seleccionada.")
        return redirect(url_for("admin_productos"))

    nuevo = Producto(
        nombre=nombre,
        descripcion=descripcion,
        cantidad_en_stock=cantidad_en_stock,
        precio=precio,
        ubicacion=ubicacion,
        color=color,
        id_proveedor=id_proveedor,
        imagen=filename
    )

    db_session.add(nuevo)
    db_session.commit()
    flash("Producto añadido correctamente.")
    return redirect(url_for("admin_productos"))


@app.route("/admin/productos/editar/<int:id_producto>", methods=["GET", "POST"])
def editar_producto(id_producto):
    producto = db_session.query(Producto).get(id_producto)

    if request.method == "POST":
        producto.nombre = request.form["nombre"]
        producto.descripcion = request.form["descripcion"]
        producto.cantidad_en_stock = int(request.form["stock"])
        producto.precio = float(request.form["precio"])
        producto.ubicacion = request.form["ubicacion"]
        producto.color = request.form["color"]

        # Imagen
        imagen_file = request.files.get("imagen")
        if imagen_file and allowed_file(imagen_file.filename):
            filename = secure_filename(imagen_file.filename)
            imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagen_file.save(imagen_path)
            producto.imagen = filename

        db_session.commit()
        flash("Producto editado correctamente.")
        return redirect(url_for("admin_productos"))

    return render_template("editar_producto.html", producto=producto)


@app.route("/admin/productos/eliminar/<int:id_producto>")
def eliminar_producto(id_producto):
    producto = db_session.query(Producto).get(id_producto)
    if producto:
        db_session.delete(producto)
        db_session.commit()
    return redirect(url_for("admin_productos"))


@app.route("/dashboard_cliente")
def dashboard_cliente():
    # Verifica si el usuario está autenticado
    if "user_id" not in session:
        return redirect(url_for("login"))

    # Redirige si el rol no es "cliente"
    if session["rol"] != "cliente":
        return redirect(url_for("dashboard_admin"))

    # Obtener el ID del cliente desde la sesión
    id_cliente = session["user_id"]
    ventas = db_session.query(Venta).filter_by(id_usuario=id_cliente).all()

    # Calcular total de compras, total gastado y la fecha de la última compra
    total_compras = len(ventas)
    total_gastado = sum(v.cantidad * v.precio_unitario for v in ventas)
    ultima_fecha = max((v.fecha_venta for v in ventas), default=None)

    # Obtener los últimos 5 productos comprados por el cliente
    productos = (
        db_session.query(Producto)
        .join(Venta, Producto.id_producto == Venta.id_producto)
        .filter(Venta.id_usuario == id_cliente)
        .order_by(Venta.fecha_venta.desc())
        .limit(5)
        .all()
    )

    # Calcular gastos por mes
    gastos_por_mes = defaultdict(float)
    for venta in ventas:
        try:
            fecha = venta.fecha_venta
            if isinstance(fecha, str):
                fecha = datetime.strptime(fecha, "%Y-%m-%d %H:%M:%S")
            mes = fecha.strftime("%B")
            gastos_por_mes[mes] += venta.cantidad * venta.precio_unitario
        except Exception as e:
            print(f"Error con venta ID {venta.id_venta}: {e}")
            continue

    #ordenar meses
    meses_ordenados = list(calendar.month_name)[1:]
    labels = []
    valores = []

    for mes in meses_ordenados:
        if mes in gastos_por_mes:
            labels.append(mes)
            valores.append(round(gastos_por_mes[mes], 2))

    return render_template(
        "dashboard_cliente.html",
        nombre=session["nombre"],
        total_compras=total_compras,
        total_gastado=total_gastado,
        ultima_fecha=ultima_fecha,
        productos=productos,
        labels=labels,
        valores=valores
    )


@app.route("/productos")
def ver_productos():
    if "user_id" not in session:
        return redirect(url_for("login"))

    productos = db_session.query(Producto).all()
    return render_template("productos.html", productos=productos)


@app.route("/comprar/<int:id_producto>", methods=["GET", "POST"])
def comprar_producto(id_producto):
    if "user_id" not in session:
        return redirect(url_for("login"))

    producto = db_session.query(Producto).get(id_producto)

    if request.method == "POST":
        cantidad = int(request.form["cantidad"])
        if cantidad <= 0 or cantidad > producto.cantidad_en_stock:
            flash("Cantidad inválida o superior al stock.")
            return redirect(url_for("comprar_producto", id_producto=id_producto))

        nueva_venta = Venta(
            id_usuario=session["user_id"],
            id_producto=producto.id_producto,
            id_proveedor=producto.id_proveedor,
            cantidad=cantidad,
            precio_unitario=producto.precio,
            fecha_venta=datetime.now()
        )

        producto.cantidad_en_stock -= cantidad

        db_session.add(nueva_venta)
        db_session.commit()

        flash("Compra realizada con éxito.")
        return redirect(url_for("ver_factura", id_venta=nueva_venta.id_venta))

    return render_template("comprar_producto.html", producto=producto)


@app.route("/factura/<int:id_venta>")
def ver_factura(id_venta):
    venta = db_session.query(Venta).get(id_venta)
    producto = db_session.query(Producto).get(venta.id_producto)
    usuario = db_session.query(Usuario).get(venta.id_usuario)

    return render_template("factura.html", venta=venta, producto=producto, usuario=usuario)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
