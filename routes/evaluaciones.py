from fastapi import APIRouter, HTTPException, Depends,Request, Response, status, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
#from bson import ObjectId
from typing import List
from models.evaluaciones import EvaluacionSave, EvaluacionList, EvaluacionQuery, EvaluacionComparaQuery
from routes.licitaciones import getLicitacion
from routes.ofertas import loadOferta
from db import get_db
from models.users import User
from auth import get_current_user
from openai import AsyncOpenAI #, OpenAI
from anthropic import AsyncAnthropic #, Anthropic
from config import settings
from datetime import datetime
import aiofiles
# from reportlab.lib.pagesizes import A4
# from reportlab.pdfgen import canvas
# from reportlab.lib.styles import getSampleStyleSheet
# from reportlab.platypus import Paragraph
import json
from utils import encryptTxt, decryptTxt
from pydantic_mongo import  PydanticObjectId


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

async def preparePromt(idl:str,idof:str,section:int,lang:str):
  oferta =  loadOferta(idof)
  licitacion =  getLicitacion(idl)

  if(oferta and licitacion):
    PLIEGO = licitacion.secciones[section].pliego
    CRITERIOS = licitacion.secciones[section].criterio
    PROPUESTA = oferta.texto
    PUNTUACION_MINIMA = "0"
    PUNTUACION_MAXIMA = str(licitacion.secciones[section].puntuacion)

    if(lang == "ga"):
      _SYS_PROMPT="Vostede é un consultor experto en tecnoloxía encargado de avaliar e puntuar as ofertas. Deberá ler o prego de condicións do documento, utilizar os criterios de valoración facilitados e valorar unha proposta asignándolle unha puntuación numérica xustificada."
      _PROMPT = f"""
          Primeiro, lea atentamente as condicións da especificación:\n<pliego>\n{PLIEGO}\n</pliego>\n\n
          Agora, considere os seguintes criterios de avaliación:\n<criteria>\n{CRITERIOS}\n</criteria>\n\n
          A continuación, avalía a seguinte proposta:\n<proposta>\n{PROPUESTA}\n</proposta>\n\n
          Analizar detidamente a proposta en relación coas condicións do documento e os criterios de avaliación previstos. Considere como a proposta cumpre ou non cada un dos criterios e condicións establecidos.\n\n
          En función da súa análise, asigne unha puntuación numérica á proposta. A puntuación debe estar entre {PUNTUACION_MINIMA} e {PUNTUACION_MAXIMA} puntos.\n\n
          Finalmente, utilizando exclusivamente coñecementos e criterios propios, expresa o grao de detalle en que a proposta responde ao prego de condicións.\n\nPresenta a túa avaliación no seguinte formato:\n\n<avaliación>\n<razoamento>\n[ Explique aquí o seu razoamento detallado, explicando como a proposta cumpre ou non os criterios e condicións e xustificando a puntuación que vai asignar]\n</reasoning>\n<detail>[Indique aquí o nivel de detalle]< /detail >\n<score>[Inserir aquí a puntuación numérica asignada]</score>\n</evaluation>\n\nAsegúrate de que a túa avaliación sexa obxectiva, en función dos criterios proporcionados e das condicións do documento, e que a súa puntuación está debidamente xustificada polo seu razoamento.
        """
        
    elif(lang == "pt"):
       _SYS_PROMPT="É um consultor especializado em tecnologia encarregado de avaliar e pontuar propostas. Deve ler as condições do documento, utilizar os critérios de avaliação fornecidos e avaliar uma proposta atribuindo-lhe uma pontuação numérica justificada."
       _PROMPT = f"""
          Em primeiro lugar, leia atentamente as condições da especificação:\n<folla>\n{PLIEGO}\n</folla>\n\n
          Considere agora os seguintes critérios de avaliação:\n<criteria>\n{CRITERIOS}\n</criteria>\n\n
          De seguida, avalie a seguinte proposta:\n<proposal>\n{PROPUESTA}\n</proposal>\n\n
          Analise cuidadosamente a proposta em relação às condições do documento e aos critérios de avaliação fornecidos. Considere a forma como a proposta cumpre ou não cada um dos critérios e condições estabelecidos. \n\n
          Com base na sua análise, atribua uma pontuação numérica à proposta. A pontuação deve estar entre {PUNTUACION_MINIMA} e {PUNTUACION_MAXIMA} pontos. \n\n
          Por fim, utilizando exclusivamente conhecimentos e critérios próprios, expresse o grau de detalhe com que a proposta responde às especificações. \n\nApresente a sua avaliação no seguinte formato:\n\n<avaliação>\n<raciocínio>\n[ Forneça aqui o seu raciocínio detalhado, explicando como a proposta cumpre ou não os critérios e condições e justificando a pontuação que irá atribuir]\n</reasoning>\n<detail>[Indique aqui o nível de detalhe]< /detail >\n< score>[Insira aqui a pontuação numérica atribuída]</score>\n</eavaliação>\n\nCertifique-se de que a sua avaliação é objetiva, baseada nos critérios fornecidos e nas condições do documento, e que a sua pontuação está devidamente justificada pelo seu raciocínio.
       """
    else:
      _SYS_PROMPT="Eres un consultor experto en tecnología con la tarea de evaluar y puntuar licitaciones. Debes leer las condiciones del pliego, utilizar los criterios de evaluación proporcionados, y evaluar una propuesta asignándole una puntuación numérica justificada."
      _PROMPT = f"""
          Primero, lee atentamente las condiciones del pliego:\n<pliego>\n{PLIEGO}\n</pliego>\n\n
          Ahora, considera los siguientes criterios de evaluación:\n<criterios>\n{CRITERIOS}\n</criterios>\n\n
          A continuación, evalúa la siguiente propuesta:\n<propuesta>\n{PROPUESTA}\n</propuesta>\n\n
          Analiza cuidadosamente la propuesta en relación con las condiciones del pliego y los criterios de evaluación proporcionados. Considera cómo la propuesta cumple o no con cada uno de los criterios y las condiciones establecidas.\n\n
          Basándote en tu análisis, asigna una puntuación numérica a la propuesta. La puntuación debe estar entre {PUNTUACION_MINIMA} y {PUNTUACION_MAXIMA} puntos.\n\n
          Por último, utilizando exclusivamente tus propios conocimientos y criterio expresa el grado de detalle en el que la propuesta responde al pliego.\n\nPresenta tu evaluación en el siguiente formato:\n\n<evaluacion>\n<razonamiento>\n[Proporciona aquí tu razonamiento detallado, explicando cómo la propuesta cumple o no con los criterios y condiciones, y justificando la puntuación que vas a asignar]\n</razonamiento>\n<detalle>[Indica aquí el grado de detalle]</detalle>\n<score>[Inserta aquí la puntuación numérica asignada]</score>\n</evaluacion>\n\nAsegúrate de que tu evaluación sea objetiva, basada en los criterios proporcionados y las condiciones del pliego, y que tu puntuación esté debidamente justificada por tu razonamiento."""


    return _SYS_PROMPT, _PROMPT
  else:
    raise HTTPException(status_code=404, detail="Oferta o licitación no encontrada")



# @router.post("/evalua" , tags=["Evaluaciones"])
# async def stream_ia(idl:str,idof:str,sect:int,current_user: User = Depends(get_current_user)):   
#   return StreamingResponse(f"{datetime.now()} HOLA MUNDO<puntuacion>15</puntuacion>")

@router.post("/evalua" , tags=["Evaluaciones"])
async def stream_ia(eval:EvaluacionQuery, request:Request, current_user: User = Depends(get_current_user)):
  _SYS_PROMPT, _PROMPT = await preparePromt(eval.idl,eval.idof,eval.sect,request.headers.get('accept-language'))

  async def response_stream(model):

        if(int(model)==1):
          chat_coroutine = client1.chat.completions.create(
              model=settings.net_model1,
              temperature=int(settings.temperature)/10,
              max_tokens=3000,
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
    evaluaciones = db.evaluaciones.find({'user':current_user.username})
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
          }],
          "user": current_user.username
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
   
# @router.get("/printeval/{idev}", tags=["Evaluaciones"])
# async def print_evaluacion(idev: str, current_user: User = Depends(get_current_user)):
#     db = get_db()
#     evaluacion = db.evaluaciones.find_one({"id": idev},
#       {"_id":0,"id":0,"id_licitacion":0}
#     )
#     if evaluacion:
#       fname = settings.uploadOf_path
#       c = canvas.Canvas(fname, pagesize=A4)
#       width, height = A4

#       styles = getSampleStyleSheet()
#       styleN = styles['Normal']

#       c.setTitle("Informe de Evaluacion")

#       c.setFont("Helvetica-Bold", 16)
#       c.drawString(30, height - 40, "Informe de Licitación")
      
      
#       c.setFont("Helvetica", 12)
#       c.drawString(30, height - 70, f"Licitación: {evaluacion['licitacion']}")
#       c.drawString(30, height - 90, f"Oferta: {evaluacion['oferta']}")
#       c.drawString(30, height - 110, f"Pmax: {evaluacion['pmax']}")
#       c.drawString(30, height - 130, f"Actualizada: {evaluacion['actualizada']}")
      

#       # Sections
#       y = height - 170
#       for section in evaluacion['sections']:
#           c.setFont("Helvetica-Bold", 14)
#           c.drawString(30, y, f"Sección: {section['seccion']}")
#           y -= 20

#           paragraph = Paragraph(decryptTxt(section["evaluacion"],settings.encrypt_key), styleN)
#           paragraph.wrapOn(c, width, 50)
#           paragraph.drawOn(c, 30, y)

#           y -= 100
#           c.drawString(50, y, f"Puntos: {section['puntos']}")
#           y -= 20
#           c.drawString(50, y, f"Actualizada: {section['actualizada']}")
#           y -= 40
      
#       c.save()
#       async with aiofiles.open(fname, mode='rb') as file:
#           pdf_content = await file.read()

#       return Response(content=pdf_content, media_type="application/pdf")



@router.post("/pliegoquery/", tags=["Licitaciones"])
async def pliego_query(
    query: str = Form(...),
    pliego: str = Form(...),
    current_user: User = Depends(get_current_user)
    ):

    async def response_stream():
        chat_coroutine = client1.chat.completions.create(
            model=settings.net_model1,
            temperature=int(settings.temperature)/10,
            max_tokens=1500,
            messages=[
              {
                "role": "system",
                "content": [
                    {
                        "type": "text",
                        "text": "Eres un consultor experto en responder preguntas sobre licitaciones de forma clara y resumida."
                    }
                ]
              },
              {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "sobre el siguiente contexto: " + pliego + " responde a la pregunta: " + query
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

    return StreamingResponse(response_stream())


#-------------------COMPARACIONES-------------------

async def preparePromtCompara(idl:str,ofA:str,ofB:str,section:int,lang:str):
  ofertaA =  loadOferta(ofA)
  ofertaB =  loadOferta(ofB)
  licitacion =  getLicitacion(idl)

  if(ofertaA and ofertaB and licitacion):
    PLIEGO = licitacion.secciones[section].pliego
    CRITERIOS = licitacion.secciones[section].criterio
    NOFERTA_A = ofertaA.oferta
    NOFERTA_B = ofertaB.oferta
    PROPUESTA_A = ofertaA.texto
    PROPUESTA_B = ofertaB.texto

    if(lang == "ga"):
      _PROMPT = f"""
        Vostede é un consultor experto en tecnoloxía encargado de avaliar e puntuar as ofertas. Debes ler as condicións do documento e utilizar os criterios de valoración facilitados para comparar dúas ofertas de dúas empresas.

        # Pasos

        1. **Revisión das Condicións do Documento**: Le e comprende atentamente as condicións do documento e os criterios de avaliación.
        2. **Avaliación da Oferta**: Examine cada oferta, analizando o "Nome da Oferta" e o "texto" proporcionado por cada empresa.
        3. **Comparación**: compara ofertas en función dos criterios proporcionados. Avaliar factores como o custo, o cumprimento técnico, a innovación, a experiencia previa e calquera outro criterio especificado nas especificacións.
        4. **Xustificación**: Describe detalladamente os motivos da túa decisión, comparando directamente os puntos fortes e débiles de cada oferta en relación cos criterios.
        5. **Determinación do gañador**: indica claramente cal das dúas ofertas é o gañador e por que.

        # Formato de saída

        A avaliación deberá presentarse nun texto detallado que inclúa:
        - Análise de cada oferta en función dos criterios dos pregos.
        - Unha comparación directa entre as dúas ofertas.
        - Unha declaración clara do nome da oferta gañadora.
        - Xustificación da elección con exemplos e referencias aos criterios de avaliación.

        **Entrada:**
        - Folla: "{PLIEGO}"
        - Criterios de avaliación: "{CRITERIOS}"
        - Oferta A:
        - Nome: "{NOFERTA_A}"
        - Texto: [{PROPUESTA_A}]
        - Oferta B:
        - Nome: "{NOFERTA_B}"
        - Texto: [{PROPUESTA_B}]

        # Exemplos de saída

        **Saída:**
        - Análise da "Solución innovadora A": [Detalles da análise baseada en criterios]
        - Análise da "Solución completa B": [Detalles da análise baseada en criterios]
        - Comparación: [Comparación detallada que destaca os puntos fortes e débiles]
        - <winner>"Solución innovadora A"</winner>
        - Debido a [motivos específicos]

        #Notas

        - Asegúrese de que a análise é imparcial e baseada estrictamente nos criterios proporcionados.
        - A comparación debe ser detallada e lóxica, evitando conxecturas infundadas.
        - Considerar calquera especificidade ou requisitos adicionais destacados nas especificacións.
      """
    elif(lang == "pt"):
       _PROMPT = f"""
          É um consultor especializado em tecnologia encarregado de avaliar e pontuar propostas. Deve ler as condições do documento e utilizar os critérios de avaliação fornecidos para comparar duas ofertas de duas empresas.

          # Passos

          1. **Revisão das Condições do Documento**: Leia e compreenda atentamente as condições do documento e os critérios de avaliação.
          2. **Avaliação da Oferta**: Examine cada oferta, analisando o “Nome da Oferta” e o “texto” fornecido por cada empresa.
          3. **Comparação**: compare as ofertas com base nos critérios fornecidos. Avalie fatores como o custo, a conformidade técnica, a inovação, a experiência anterior e quaisquer outros critérios especificados nas especificações.
          4. **Justificação**: Descreva detalhadamente os motivos da sua decisão, comparando diretamente os pontos fortes e fracos de cada oferta em relação aos critérios.
          5. **Determinação do Vencedor**: Indique claramente qual das duas ofertas é a vencedora e porquê.

          # Formato de saída

          A avaliação deverá ser apresentada num texto detalhado que inclua:
          - Uma análise de cada oferta com base nos critérios do caderno de encargos.
          - Uma comparação direta entre as duas ofertas.
          - Uma declaração clara do nome da proposta vencedora.
          - Justificação da escolha com exemplos e referências aos critérios de avaliação.

          **Entrada:**
          - Folha: "{PLIEGO}"
          - Critérios de avaliação: "{CRITERIOS}"
          - Oferta A:
          - Nome: "{NOFERTA_A}"
          - Texto: [{PROPUESTA_A}]
          - Oferta B:
          - Nome: "{NOFERTA_B}"
          - Texto: [{PROPUESTA_B}]

          # Exemplos de saída

          **Saída:**
          - Análise da "Solução Inovadora A": [Detalhes da análise baseada em critérios]
          - Análise da "Solução Completa B": [Detalhes da análise baseada em critérios]
          - Comparação: [Comparação detalhada destacando os pontos fortes e fracos]
          - <winner>"Solução Inovadora A"</winner>
          - Devido a [motivos específicos]

          #Notas

          - Certifique-se de que a análise é imparcial e baseada estritamente nos critérios fornecidos.
          - A comparação deve ser detalhada e lógica, evitando conjeturas infundadas.
          - Considere qualquer especificidade ou requisitos adicionais destacados nas especificações.
       """

    else:
      _PROMPT = f"""
          Eres un consultor experto en tecnología con la tarea de evaluar y puntuar licitaciones. Debes leer las condiciones del pliego y utilizar los criterios de evaluación proporcionados para comparar dos ofertas de dos empresas.

          # Steps

          1. **Revisión de Condiciones del Pliego**: Lee y comprende cuidadosamente las condiciones del pliego y los criterios de evaluación.
          2. **Evaluación de Ofertas**: Examina cada oferta, analizando el "Nombre de la oferta" y el "texto" proporcionado por cada empresa.
          3. **Comparación**: Compara las ofertas basándote en los criterios proporcionados. Evalúa factores como costo, cumplimiento técnico, innovación, experiencia previa, y cualquier otro criterio especificado en el pliego.
          4. **Justificación**: Describe detalladamente las razones detrás de tu decisión, comparando directamente las fortalezas y debilidades de cada oferta en relación con los criterios.
          5. **Determinación del Ganador**: Indica claramente cuál de las dos ofertas es la ganadora y por qué.

          # Output Format

          La evaluación debe presentarse en un texto detallado que incluya:
          - Un análisis de cada oferta basado en los criterios del pliego.
          - Una comparación directa entre las dos ofertas.
          - Una clara declaración del nombre de la oferta ganadora.
          - Justificación de la elección con ejemplos y referencias a los criterios de evaluación.

          **Input:**
          - Pliego: "{PLIEGO}"
          - Criterios de evaluación: "{CRITERIOS}"
          - Oferta A: 
            - Nombre: "{NOFERTA_A}"
            - Texto: [{PROPUESTA_A}]
          - Oferta B:
            - Nombre: "{NOFERTA_B}"
            - Texto: [{PROPUESTA_B}]

          # Output example

          **Output:**
          - Análisis de "Solución Innovadora A": [Detalles del análisis basado en criterios]
          - Análisis de "Solución Completa B": [Detalles del análisis basado en criterios]
          - Comparación: [Comparación detallada resaltando fortalezas y debilidades]
          - <winner>"Solución Innovadora A"</winner>
          - Debido a [razones específicas]

          # Notes

          - Asegúrate de que el análisis sea imparcial y basado estrictamente en los criterios proporcionados.
          - La comparación debe ser detallada y lógica, evitando conjeturas no fundamentadas.
          - Considera cualquier especificidad o requerimiento adicional destacado en el pliego."""
      
    return _PROMPT
  else:
    raise HTTPException(status_code=404, detail="Oferta o licitación no encontrada")
  
@router.post("/compara" , tags=["Evaluaciones"])
async def stream_compara_ia(eval:EvaluacionComparaQuery,request:Request, current_user: User = Depends(get_current_user)):
  _PROMPT = await preparePromtCompara(eval.idl,eval.ofA,eval.ofB,eval.sect,request.headers.get('accept-language'))

  async def response_stream(model):

    if(settings.comp_model==1):
      chat_coroutine = client1.chat.completions.create(
          model=settings.net_model1,
          temperature=int(settings.temperature)/10,
          max_tokens=4000,
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
          max_tokens=4000,
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


#-----------------------BACKGROUND TASK-----------------------------

# def comparar_ofertas_seccion(idlicitacion:str,seccion:int):
#     db = get_db()
#     ofertas = list(db.ofertas.find({"id_licitacion": idlicitacion}))
#     licitacion = db.licitaciones.find_one(
#        {"id": idlicitacion},
#        {"secciones":{"$arrayElemAt":["$secciones",seccion]}}
#     )

#     #check if ofertas length >0
#     if len(ofertas) == 0:
#       raise HTTPException(status_code=404, detail="Oferta no encontrada")
    
#     #check if licitacion exists
#     if not licitacion:
#       raise HTTPException(status_code=404, detail="Licitacion no encontrada")
    

#     # f = open("./test.txt", "a")
#     # f.write(licitacion["secciones"]['tabtxt'])
#     # f.close()
        
#     for of in ofertas:
#       completion  = client1.chat.completions.create(
#         model=settings.net_model1,
#         temperature=int(settings.temperature)/10,
#         max_tokens=3000,
#         messages=[
#           {
#             "role": "system",
#             "content": [
#                 {
#                     "type": "text",
#                     "text": "Eres un consultor experto en responder preguntas sobre licitaciones de forma clara y resumida."
#                 }
#             ]
#           },
#           {
#             "role": "user",
#             "content": [
#                 {
#                     "type": "text",
#                     "text": "sobre el siguiente contexto:  responde a la pregunta: " 
#                 }
#             ]
#         }
#         ],
#         stream=False,
#       )
#       completion.choices[0].message.content
      

#     return "OK"


# @router.post("/comparetab/")
# async def compare_tab(idlicitacion: str, seccion:int, background_tasks: BackgroundTasks, current_user: User = Depends(get_current_user)):
#   background_tasks.add_task(comparar_ofertas_seccion, idlicitacion, seccion)
#   return {"message": "Notification sent in the background"}
