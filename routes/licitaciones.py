import os
import shutil
from fastapi import APIRouter, HTTPException, Depends, Form, File, UploadFile, status
from fastapi.security import OAuth2PasswordBearer
from typing import List
from db import get_db
from datetime import datetime
from models.licitaciones import Licitacion, LicitaList
from models.users import User
from auth import get_current_user
from utils import loadPagesfromPDF
from pydantic_mongo import  PydanticObjectId

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def getLicitacion(idl):
    if(idl!='0'):
        db = get_db()
        licitacion = db.licitaciones.find_one({"id": idl})
        if licitacion:
            return Licitacion(**licitacion)
        else:
            raise HTTPException(status_code=404, detail="Licitación no encontrada")
    else:
        return Licitacion() 
    
@router.get("/licitaciones/", response_model=List[LicitaList], tags=["Licitaciones"])
async def read_licitaciones(current_user: User = Depends(get_current_user)):
    db = get_db()
    licitaciones = db.licitaciones.find({'user':current_user.username})
    return [LicitaList(**licitacion) for licitacion in licitaciones]

@router.get("/licitaciones/{id}", response_model=Licitacion , tags=["Licitaciones"])
async def read_licitacion(id: str, current_user: User = Depends(get_current_user)):
    return getLicitacion(id)

@router.post("/licitaciones/", tags=["Licitaciones"])
async def create_licitacion(licitacion: Licitacion, current_user: User = Depends(get_current_user)):
    db = get_db()
    licitacion_dict = licitacion.dict()
    licitacion_dict["id"] = str(PydanticObjectId())
    licitacion_dict["user"] = current_user.username
    result = db.licitaciones.insert_one(licitacion_dict)

    if result:
        return {"msg": str(result.inserted_id)}
    raise HTTPException(status_code=404, detail="Error al guardae licitacion")

@router.put("/licitaciones/{id}", tags=["Licitaciones"])
async def update_licitacion(id: str, licitacion: Licitacion, current_user: User = Depends(get_current_user)):
    db = get_db()
    licitacion_dict = licitacion.dict()
    updated_licitacion = db.licitaciones.update_one(
        {"id": id},
        {"$set": licitacion_dict}
    )
    if updated_licitacion:
        return {"msg": updated_licitacion.modified_count}

    raise HTTPException(status_code=404, detail="Licitación no encontrada")
    # print(licitacion.dict(), id)
    # return "OK"

@router.delete("/licitaciones/{id}",  status_code=status.HTTP_204_NO_CONTENT, tags=["Licitaciones"])
async def delete_licitacion(id: str, current_user: User = Depends(get_current_user)):
    db = get_db()
    result = db.licitaciones.delete_one({"id": id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Licitación no encontrada")
    else:
        return {"msg":result.deleted_count }


@router.post("/uploadpliegofile/", tags=["Licitaciones"])
async def upload_pliego_file(
    file: UploadFile = File(...), 
    id: str = Form(...),
    current_user: User = Depends(get_current_user)
    ):

    try:
        #save file to disk with random uuid
        upload_dir = './static/pliegos/' #settings.uploadPL_path
        
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)


        file_location = os.path.join(upload_dir, file.filename) #file.filename
        
        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)

        db = get_db()

        db.licitaciones.update_one(
            {"id": id},
            {"$set": {
                "licitacion_fname": file.filename,
            }},upsert=True
        )
        
        return file.filename
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo subir el archivo: {str(e)}")
    

@router.post("/loadpages/", tags=["Licitaciones"])
async def upload_file(
    docname: str = Form(...),
    pages: str = Form(...),
    current_user: User = Depends(get_current_user)
    ):

    try:
        return loadPagesfromPDF(docname,pages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo subir el archivo: {str(e)}")


#lo tengo en evaluaviones pk allí estan los objetos y key de openai
#@router.post("/pliegoquery/", tags=["Licitaciones"])
