#https://pypi.org/project/pydantic-mongo/

from bson import ObjectId
from pydantic import BaseModel
from pydantic_mongo import  PydanticObjectId
from pymongo import MongoClient
from datetime import datetime
from typing import Optional, List
import os

class OfertasField(BaseModel):
    id: PydanticObjectId = None
    alias: str = ""
    fecha: datetime = None

class ContextField(BaseModel):
    tabtxt: str = ""
    puntuacion: int = 0
    pliego: str = ""
    criterio: str = ""

class Licitacion(BaseModel):
    id: Optional[PydanticObjectId] = None
    nombre: str = ""
    actualizada: datetime = datetime.now()
    estado: str = ""
    observaciones: str = ""
    enlace: str = ""
    pmax:int = 0
    ofertas: Optional[List[OfertasField]] = []
    secciones: List[ContextField] = []
    

class LicitaList(BaseModel):
    id: Optional[PydanticObjectId] = None
    nombre: str = ""
    actualizada: datetime = datetime.now()
    estado: str = ""


class OfertaDoc(BaseModel):
    id: Optional[PydanticObjectId] = None
    id_licitacion: PydanticObjectId = None
    oferta: str = ""
    fecha: datetime = datetime.now()
    texto: str = ""