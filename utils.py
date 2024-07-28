from cryptography.fernet import Fernet

def encryptTxt(text, key):
  f = Fernet(key)
  return f.encrypt(text.encode()).decode()  

def decryptTxt(text, key):
  f = Fernet(key)
  return f.decrypt(text.encode()).decode()
