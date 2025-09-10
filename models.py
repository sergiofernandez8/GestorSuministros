from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from db import Base


class Usuario(Base):
    __tablename__ = 'usuarios'

    id_usuario = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(255), nullable=False)
    correo = Column(String(255), unique=True, nullable=False)
    contraseña = Column(String(255), nullable=False)
    rol = Column(String(50), nullable=False)
    __table_args__ = (
        CheckConstraint("rol IN ('cliente', 'administrador')", name='check_rol'),
    )

    def set_password(self, password):
        self.contraseña = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.contraseña, password)


class Proveedor(Base):
    __tablename__ = "proveedores"

    id_proveedor = Column(Integer, primary_key=True, autoincrement=True)
    nombre_empresa = Column(Text, nullable=False)
    telefono = Column(Text)
    direccion = Column(Text)
    cif = Column(Text, unique=True)
    porcentaje_descuento = Column(Float)
    iva = Column(Float)

    productos = relationship("Producto", back_populates="proveedor")
    compras = relationship("Compra", back_populates="proveedor")
    ventas = relationship("Venta", back_populates="proveedor")


class Producto(Base):
    __tablename__ = "productos"

    id_producto = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(Text, nullable=False)
    descripcion = Column(Text)
    cantidad_en_stock = Column(Integer, nullable=False, default=0)
    precio = Column(Float, nullable=False)
    ubicacion = Column(Text)
    color = Column(Text)
    imagen = Column(Text)  # NUEVO CAMPO
    id_proveedor = Column(Integer, ForeignKey("proveedores.id_proveedor"), nullable=False)

    proveedor = relationship("Proveedor", back_populates="productos")
    compras = relationship("Compra", back_populates="producto")
    ventas = relationship("Venta", back_populates="producto")


class Compra(Base):
    __tablename__ = "compras"

    id_compra = Column(Integer, primary_key=True, autoincrement=True)
    id_proveedor = Column(Integer, ForeignKey("proveedores.id_proveedor"), nullable=False)
    id_producto = Column(Integer, ForeignKey("productos.id_producto"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    descuento = Column(Float, default=0.0)
    iva = Column(Float, default=21.0)
    fecha_compra = Column(DateTime, default=datetime.utcnow)

    proveedor = relationship("Proveedor", back_populates="compras")
    producto = relationship("Producto", back_populates="compras")


class Venta(Base):
    __tablename__ = "ventas"

    id_venta = Column(Integer, primary_key=True, autoincrement=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    id_producto = Column(Integer, ForeignKey("productos.id_producto", ondelete="SET NULL"), nullable=True)
    id_proveedor = Column(Integer, ForeignKey("proveedores.id_proveedor"), nullable=False)
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    fecha_venta = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario")
    producto = relationship("Producto", back_populates="ventas", passive_deletes=True)
    proveedor = relationship("Proveedor", back_populates="ventas")

