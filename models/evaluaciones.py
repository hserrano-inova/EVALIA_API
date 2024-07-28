from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from pydantic_mongo import  PydanticObjectId

class EvaluacionSave(BaseModel):
    id: Optional[PydanticObjectId] = None
    id_licitacion:str = ""
    licitacion:str
    oferta: str = ""
    seccion: str = ""
    evaluacion: str = ""
    puntos:int = 0
    actualizada:Optional[datetime] =  None
    pmax:int = 0

class EvaluacionList(BaseModel):
    id: PydanticObjectId
    id_licitacion:str
    licitacion:str
    oferta: str
    actualizada:Optional[datetime]
    pmax:int

class EvaluacionQuery(BaseModel):
    idl:str
    idof:str
    sect:int
    model:int
