from typing import List, Optional
from pydantic import BaseModel, Field


class PersonSchema(BaseModel):
    name: str
    age: int
    country: str


class InvoiceSchema(BaseModel):
    tipo_doc: str = Field(
        description="Código del documento (ej: 30=Factura, 33=Factura Electrónica, 60=Nota Crédito)",
    )
    folio: str = Field(description="Número de folio de la factura")
    rut_contraparte: str = Field(
        description="RUT del emisor o receptor (formato chileno: XX.XXX.XXX-X)"
    )
    razon_social: Optional[str] = Field(None, description="Nombre o razón social")
    fecha_emision: str = Field(description="Fecha en formato DD-MM-YYYY o similar")
    monto_neto: float = Field(description="Monto neto sin IVA")
    monto_iva: float = Field(description="Monto IVA recuperable")
    monto_total: float = Field(description="Monto total de la factura")
    producto_o_descripcion: Optional[str] = Field(
        None, description="Descripción breve del producto/servicio si aplica"
    )


class InvoiceList(BaseModel):
    invoices: List[InvoiceSchema]
