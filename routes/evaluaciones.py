from fastapi import APIRouter, HTTPException, Depends, Response, status
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from bson import ObjectId
from typing import List
from models.evaluaciones import EvaluacionSave, EvaluacionList, EvaluacionQuery
from routes.licitaciones import getLicitacion
from routes.ofertas import loadOferta
from db import get_db
from models.users import User
from auth import get_current_user
from openai import AsyncOpenAI #, OpenAI
from anthropic import AsyncAnthropic #, Anthropic
from config import settings
from pydantic_mongo import  PydanticObjectId
from datetime import datetime
import aiofiles
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
import json
from utils import encryptTxt, decryptTxt


router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

client1 = AsyncOpenAI(
  api_key=settings.api_key1
)
client2 = AsyncAnthropic(
  api_key=settings.api_key2
)
# client1 = OpenAI(
#   api_key=settings.api_key,
# )


# @router.post("/evalua")
# async def stream_text(): 
#   message = await client1.chat.completions.create(
#       model=settings.net_model,
#       messages=[{"role": "user", "content": "dime lo que sepas sobre Julio Cesar"}],
#       max_tokens=100,
#       stream=False,
#   )
#   return message.choices[0].message.content

async def preparePromt(idl:str,idof:str,section:int):
  oferta =  loadOferta(idof)
  licitacion =  getLicitacion(idl)

  if(oferta and licitacion):
    PLIEGO = licitacion.secciones[section].pliego
    CRITERIOS = licitacion.secciones[section].criterio
    PROPUESTA = oferta.texto
    PUNTUACION_MINIMA = "0"
    PUNTUACION_MAXIMA = str(licitacion.secciones[section].puntuacion)
    _SYS_PROMPT="Eres un consultor experto en tecnología con la tarea de evaluar y puntuar licitaciones. Debes leer las condiciones del pliego, utilizar los criterios de evaluación proporcionados, y evaluar una propuesta asignándole una puntuación numérica justificada."
    _PROMPT = f"""
        Primero, lee atentamente las condiciones del pliego:\n<pliego>\n{PLIEGO}\n</pliego>\n\n
        Ahora, considera los siguientes criterios de evaluación:\n<criterios>\n{CRITERIOS}\n</criterios>\n\n
        A continuación, evalúa la siguiente propuesta:\n<propuesta>\n{PROPUESTA}\n</propuesta>\n\n
        Analiza cuidadosamente la propuesta en relación con las condiciones del pliego y los criterios de evaluación proporcionados. Considera cómo la propuesta cumple o no con cada uno de los criterios y las condiciones establecidas.\n\n
        Basándote en tu análisis, asigna una puntuación numérica a la propuesta. La puntuación debe estar entre {PUNTUACION_MINIMA} y {PUNTUACION_MAXIMA} puntos.\n\n
        Por último, utilizando exclusivamente tus propios conocimientos y criterio expresa el grado de detalle en el que la propuesta responde al pliego.\n\nPresenta tu evaluación en el siguiente formato:\n\n<evaluacion>\n<razonamiento>\n[Proporciona aquí tu razonamiento detallado, explicando cómo la propuesta cumple o no con los criterios y condiciones, y justificando la puntuación que vas a asignar]\n</razonamiento>\n<detalle>[Indica aquí el grado de detalle]</detalle>\n<puntuacion>[Inserta aquí la puntuación numérica asignada]</puntuacion>\n</evaluacion>\n\nAsegúrate de que tu evaluación sea objetiva, basada en los criterios proporcionados y las condiciones del pliego, y que tu puntuación esté debidamente justificada por tu razonamiento."""
    return _SYS_PROMPT, _PROMPT
  else:
    raise HTTPException(status_code=404, detail="Oferta o licitación no encontrada")



# @router.post("/evalua" , tags=["Evaluaciones"])
# async def stream_ia(idl:str,idof:str,sect:int,current_user: User = Depends(get_current_user)):   
#   return StreamingResponse(f"{datetime.now()} HOLA MUNDO<puntuacion>15</puntuacion>")

@router.post("/evalua" , tags=["Evaluaciones"])
async def stream_ia(eval:EvaluacionQuery,current_user: User = Depends(get_current_user)):
  _SYS_PROMPT, _PROMPT = await preparePromt(eval.idl,eval.idof,eval.sect)

  async def response_stream(model):

        if(int(model)==1):
          chat_coroutine = client1.chat.completions.create(
              model=settings.net_model1,
              temperature=int(settings.temperature)/10,
              messages=[
                {
                  "role": "system",
                  "content": [
                      {
                          "type": "text",
                          "text": _SYS_PROMPT
                      }
                  ]
                },
                {
                  "role": "user",
                  "content": [
                      {
                          "type": "text",
                          "text": _PROMPT
                      }
                  ]
              }
              ],
              stream=True,
          )
          async for chunk in await chat_coroutine:
            #yield json.dumps(chunk.model_dump(), ensure_ascii=False) + "\n"
            if chunk.choices[0].delta.content is not None:
                yield chunk.choices[0].delta.content

        else:
          async with client2.messages.stream(
              model=settings.net_model2,
              temperature=int(settings.temperature)/10,
              max_tokens=2500,
              system=_SYS_PROMPT,
              messages=[
                {
                  "role": "user",
                  "content": [
                      {
                          "type": "text",
                          "text": _PROMPT
                      }
                  ]
              }
              ],
          ) as stream:
              async for event in stream:
                if event.type == "text":
                  yield event.text
		#elif event.type == 'content_block_stop':
		#    print('\n\ncontent block finished accumulating:', event.content_block)
          
          #https://github.com/anthropics/anthropic-sdk-python/blob/main/examples/messages_stream.py

  return StreamingResponse(response_stream(eval.model))



@router.get("/evaluaciones/licita/{idl}", response_model=List[EvaluacionList], tags=["Evaluaciones"])
async def read_evaluacion_licita(idl: str, current_user: User = Depends(get_current_user)):
    db = get_db()
    evaluaciones = db.evaluaciones.find({"id_licitacion": idl},{"_id":0})
    if evaluaciones:
        return [EvaluacionList(**evaluacion) for evaluacion in evaluaciones]
    raise HTTPException(status_code=404, detail="Evaluacion no encontrada")

@router.get("/evaluaciones/{idev}", tags=["Evaluaciones"])
async def read_evaluacion(idev: str, current_user: User = Depends(get_current_user)):
    db = get_db()
    evaluacion = db.evaluaciones.find_one({"id": idev},{"_id":0})
    if evaluacion:
        for i,x in enumerate(evaluacion["sections"]):
          #print(decryptTxt(x["evaluacion"],settings.encrypt_key))
          evaluacion["sections"][i]["evaluacion"] = decryptTxt(x["evaluacion"],settings.encrypt_key),
        return evaluacion
    raise HTTPException(status_code=404, detail="Evaluacion no encontrada")

@router.get("/evaluaciones/", response_model=List[EvaluacionList], tags=["Evaluaciones"])
async def create_evaluacion(current_user: User = Depends(get_current_user)):
    db = get_db()
    evaluaciones = db.evaluaciones.find()
    return [EvaluacionList(**evaluacion) for evaluacion in evaluaciones]

@router.post("/evaluaciones", tags=["Evaluaciones"])
async def save_evaluacion(data: EvaluacionSave, current_user: User = Depends(get_current_user)):
    db = get_db()
    evaluacion_dict = data.dict()
    evdoc = db.evaluaciones.find_one(
       {
          "id_licitacion": evaluacion_dict["id_licitacion"],
          "licitacion": evaluacion_dict["licitacion"],
          "oferta": evaluacion_dict["oferta"],
      })
    if evdoc: 
      #$PUSH SI NO EXISTE LA SECCION
      x = db.evaluaciones.update_one(
        {"id": evdoc["id"],"sections.seccion": { "$ne": evaluacion_dict["seccion"] }},
        {"$set": {
            "pmax": evaluacion_dict["pmax"],
            "actualizada": datetime.now()
          },
          "$push": {
            "sections": {
                "seccion":evaluacion_dict["seccion"],
                "evaluacion": encryptTxt(evaluacion_dict["evaluacion"],settings.encrypt_key),
                "puntos": evaluacion_dict["puntos"],
                "actualizada": datetime.now()
            }
          }
        }
      )
      #UPDATE SI EXISTE LA SECCION
      x = db.evaluaciones.update_one(
        {"id": evdoc["id"],"sections.seccion":  evaluacion_dict["seccion"] },
        {"$set": {
            "pmax": evaluacion_dict["pmax"],
            "actualizada": datetime.now(),
            "sections.$[elem].seccion":evaluacion_dict["seccion"],
            "sections.$[elem].evaluacion": encryptTxt(evaluacion_dict["evaluacion"],settings.encrypt_key),
            "sections.$[elem].puntos": evaluacion_dict["puntos"],
            "sections.$[elem].actualizada": datetime.now()
          }
        },
        array_filters=[{"elem.seccion": evaluacion_dict["seccion"]}]
      )
       
    else: #INSERT SI NO EXISTE LA EVALUACION
       x = db.evaluaciones.insert_one({
          "id": str(PydanticObjectId()),
          "id_licitacion": evaluacion_dict["id_licitacion"],
          "licitacion": evaluacion_dict["licitacion"],
          "oferta": evaluacion_dict["oferta"],
          "pmax": evaluacion_dict["pmax"],
          "actualizada": datetime.now(),
          "sections": [{
              "seccion":evaluacion_dict["seccion"],
              "evaluacion": encryptTxt(evaluacion_dict["evaluacion"],settings.encrypt_key),
              "puntos": evaluacion_dict["puntos"],
              "actualizada": datetime.now()
          }]
       })
       
    return 1

@router.delete("/evaluaciones/{idev}",  status_code=status.HTTP_204_NO_CONTENT, tags=["Evaluaciones"])
async def delete_evaluacion(idev: str, current_user: User = Depends(get_current_user)):
    db = get_db()
    result = db.evaluaciones.delete_one({"id": idev})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Evaluacion no encontrada")
    else:
        return {"msg":result.deleted_count }
   
@router.get("/printeval/{idev}", tags=["Evaluaciones"])
async def print_evaluacion(idev: str, current_user: User = Depends(get_current_user)):
    db = get_db()
    evaluacion = db.evaluaciones.find_one({"id": idev},
      {"_id":0,"id":0,"id_licitacion":0}
    )
    if evaluacion:
      fname = settings.uploadOf_path
      c = canvas.Canvas(fname, pagesize=A4)
      width, height = A4

      styles = getSampleStyleSheet()
      styleN = styles['Normal']

      c.setTitle("Informe de Evaluacion")

      c.setFont("Helvetica-Bold", 16)
      c.drawString(30, height - 40, "Informe de Licitación")
      
      
      c.setFont("Helvetica", 12)
      c.drawString(30, height - 70, f"Licitación: {evaluacion['licitacion']}")
      c.drawString(30, height - 90, f"Oferta: {evaluacion['oferta']}")
      c.drawString(30, height - 110, f"Pmax: {evaluacion['pmax']}")
      c.drawString(30, height - 130, f"Actualizada: {evaluacion['actualizada']}")
      

      # Sections
      y = height - 170
      for section in evaluacion['sections']:
          c.setFont("Helvetica-Bold", 14)
          c.drawString(30, y, f"Sección: {section['seccion']}")
          y -= 20

          paragraph = Paragraph(decryptTxt(section["evaluacion"],settings.encrypt_key), styleN)
          paragraph.wrapOn(c, width, 50)
          paragraph.drawOn(c, 30, y)

          y -= 100
          c.drawString(50, y, f"Puntos: {section['puntos']}")
          y -= 20
          c.drawString(50, y, f"Actualizada: {section['actualizada']}")
          y -= 40
      
      c.save()
      async with aiofiles.open(fname, mode='rb') as file:
          pdf_content = await file.read()

      return Response(content=pdf_content, media_type="application/pdf")

