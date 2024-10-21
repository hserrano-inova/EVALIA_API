from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from pydantic_mongo import  PydanticObjectId

class ComparacionSave(BaseModel):
    id: Optional[PydanticObjectId] = None
    id_licitacion:str = ""
    licitacion:str
    ofA: str = ""
    ofB: str = ""
    seccion: str = ""
    comparacion: str = ""
    actualizada:Optional[datetime] =  None
    user: str = ""
    
class ComparacionList(BaseModel):
    id: PydanticObjectId
    id_licitacion:str
    licitacion:str
    ofA: str
    ofB: str
    actualizada:Optional[datetime]