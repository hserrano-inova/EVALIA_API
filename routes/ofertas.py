from fastapi import APIRouter, HTTPException, Depends, Form, File, UploadFile, status
from fastapi.security import OAuth2PasswordBearer
import shutil
import os
from db import get_db
from bson import ObjectId
from models.users import User
from config import settings
from models.licitaciones import OfertaDoc
from auth import get_current_user
from datetime import datetime
from pydantic_mongo import  PydanticObjectId
from pypdf import PdfReader
from cleantext import clean
from utils import encryptTxt, decryptTxt

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def loadOferta(idof):
    db = get_db()
    oferta = db.ofertas.find_one({"id": idof})
    if oferta:
        oferta.texto = decryptTxt(oferta.texto, settings.encrypt_key)
        return OfertaDoc(**oferta)
    else:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")
    
def insertOF(db, file,licitaid,alias) -> str:
    upload_dir = "uploads"
    
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)

    file_location = settings.uploadOf_path # os.path.join(upload_dir,'temp.pdf' ) #file.filename
    
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
    
    reader = PdfReader(file_location)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"

    clean_text = clean(text,
                   fix_unicode=True,               # fix various unicode errors
                   to_ascii=True,                  # transliterate to closest ASCII representation
                   lower=True,                     # lowercase text
                   no_line_breaks=True,            # fully strip line breaks
                   no_urls=False,                   # replace all URLs with a special token
                   no_emails=True,                 # replace all email addresses with a special token
                   no_phone_numbers=True,          # replace all phone numbers with a special token
                   no_numbers=False,                # replace all numbers with a special token
                   no_digits=False,                 # replace all digits with a special token
                   no_currency_symbols=True,       # replace all currency symbols with a special token
                   no_punct=False,                  # remove punctuations
                #    replace_with_punct="",          # instead of removing punctuations you may replace them
                #    replace_with_url="<URL>",
                #    replace_with_email="<EMAIL>",
                #    replace_with_phone_number="<PHONE>",
                #    replace_with_number="<NUMBER>",
                #    replace_with_digit="0",
                #    replace_with_currency_symbol="<CUR>",
                   lang="es"                        # set to 'es' for Spanish text
                   )
    
    _id = PydanticObjectId()
    of =OfertaDoc(
        id = _id,
        id_licitacion = licitaid,
        alias=alias,
        fecha = datetime.now(),
        #texto=clean_text
        texto=encryptTxt(clean_text, settings.encrypt_key),
    )

    resp = db.ofertas.insert_one(of.dict())

    return str(_id)

@router.post("/uploadfile/", tags=["Ofertas"])
async def upload_file(
    file: UploadFile = File(...), 
    id: str = Form(...),
    alias: str = Form(...),
    current_user: User = Depends(get_current_user)
    ):

    try:
        db = get_db()

        ofid = insertOF(db, file, id,alias)

        db.licitaciones.update_one(
            {"id": id},
            {"$push": {"ofertas": {
                "id": ofid,
                "alias": alias,
                "fecha": datetime.now()
            }}}
        )
        
        return {"info": f"Archivo subido correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo subir el archivo: {str(e)}")

# @router.get("/oferta/{id}", response_model=OfertaDoc)
# async def load_oferta(id: str, current_user: User = Depends(get_current_user)):
#     return loadOferta(id)

@router.delete("/oferta/{idof}/{idlicita}",  tags=["Ofertas"], status_code=status.HTTP_204_NO_CONTENT)
async def delete_licitacion(idof: str, idlicita: str, current_user: User = Depends(get_current_user)):
    db = get_db()
    db.ofertas.delete_one({"id": idof})
    result = db.licitaciones.update_one(
        {"id": idlicita},
        {"$pull": {"ofertas": {"id": idof}}}
    )

    return result.modified_count