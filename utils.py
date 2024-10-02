import os
from cryptography.fernet import Fernet
from pypdf import PdfReader

def encryptTxt(text, key):
  f = Fernet(key)
  return f.encrypt(text.encode()).decode()  

def decryptTxt(text, key):
  f = Fernet(key)
  return f.decrypt(text.encode()).decode()

def loadPagesfromPDF(path:str, paginas:str) -> str:

  text=''

  try:
    paginas = list(map(int, paginas.split(',')))
    path='./static/pliegos/' + path
    if not os.path.exists(path):
      return('no exiteste')

    reader = PdfReader(path)
    for pag in paginas:
      text += reader.pages[pag].extract_text() + "\n"

  except Exception as e:
    return e

  return text