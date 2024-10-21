from fastapi import APIRouter, HTTPException, Depends, Response, status, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from db import get_db
from models.users import User
from auth import get_current_user
from models.comparaciones import ComparacionSave, ComparacionList
from datetime import datetime
from typing import List
from pydantic_mongo import  PydanticObjectId


router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@router.get("/comparaciones/", response_model=List[ComparacionList], tags=["Comparaciones"])
async def create_comparacion(current_user: User = Depends(get_current_user)):
    db = get_db()
    comparaciones = db.comparaciones.find({'user':current_user.username})
    return [ComparacionList(**comparacion) for comparacion in comparaciones]

@router.get("/comparaciones/{idcomp}", tags=["Comparaciones"])
async def read_comparacion(idcomp: str, current_user: User = Depends(get_current_user)):
    db = get_db()
    comparacion = db.comparaciones.find_one({"id": idcomp},{"_id":0})
    if comparacion:
        for i,x in enumerate(comparacion["sections"]):
          #print(decryptTxt(x["comparacion"],settings.encrypt_key))
          comparacion["sections"][i]["comparacion"] = x["comparacion"],
        return comparacion
    raise HTTPException(status_code=404, detail="Comparacion no encontrada")

@router.get("/comparaciones/licita/{idl}", response_model=List[ComparacionList], tags=["Comparaiones"])
async def read_comparacion_licita(idl: str, current_user: User = Depends(get_current_user)):
    db = get_db()
    comparaciones = db.comparaciones.find({"id_licitacion": idl},{"_id":0})
    if comparaciones:
        return [ComparacionList(**comparacion) for comparacion in comparaciones]
    raise HTTPException(status_code=404, detail="Comparaciones no encontrada")

@router.post("/comparaciones", tags=["Comparaciones"])
async def save_Comparacion(data: ComparacionSave, current_user: User = Depends(get_current_user)):
    db = get_db()
    Comparacion_dict = data.dict()
    evdoc = db.comparaciones.find_one(
       {
          "id_licitacion": Comparacion_dict["id_licitacion"],
          "ofA": Comparacion_dict["ofA"],
          "ofB": Comparacion_dict["ofB"],
      })
    if evdoc: 
      #$PUSH SI NO EXISTE LA SECCION
      x = db.comparaciones.update_one(
        {"id": evdoc["id"],"sections.seccion": { "$ne": Comparacion_dict["seccion"] }},
        {"$set": {
            "actualizada": datetime.now()
          },
          "$push": {
            "sections": {
                "seccion":Comparacion_dict["seccion"],
                "comparacion": Comparacion_dict["comparacion"],
                "actualizada": datetime.now()
            }
          }
        }
      )
      #UPDATE SI EXISTE LA SECCION
      x = db.comparaciones.update_one(
        {"id": evdoc["id"],"sections.seccion":  Comparacion_dict["seccion"] },
        {"$set": {
            "actualizada": datetime.now(),
            "sections.$[elem].seccion":Comparacion_dict["seccion"],
            "sections.$[elem].comparacion": Comparacion_dict["comparacion"],
            "sections.$[elem].actualizada": datetime.now()
          }
        },
        array_filters=[{"elem.seccion": Comparacion_dict["seccion"]}]
      )
       
    else: #INSERT SI NO EXISTE LA Comparacion
       x = db.comparaciones.insert_one({
          "id": str(PydanticObjectId()),
          "id_licitacion": Comparacion_dict["id_licitacion"],
          "licitacion": Comparacion_dict["licitacion"],
          "ofA": Comparacion_dict["ofA"],
          "ofB": Comparacion_dict["ofB"],
          "actualizada": datetime.now(),
          "sections": [{
              "seccion":Comparacion_dict["seccion"],
              "comparacion": Comparacion_dict["comparacion"],
              "actualizada": datetime.now()
          }],
          "user": current_user.username
       })
       
    return 1

@router.delete("/comparaciones/{idcomp}",  status_code=status.HTTP_204_NO_CONTENT, tags=["Comparaciones"])
async def delete_Comparacion(idcomp: str, current_user: User = Depends(get_current_user)):
    db = get_db()
    result = db.comparaciones.delete_one({"id": idcomp})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Comparacion no encontrada")
    else:
        return {"msg":result.deleted_count }
   