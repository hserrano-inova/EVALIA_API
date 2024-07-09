uvicorn main:app --reload --host 0.0.0.0 --port 8000
#gunicorn main:app -b 0.0.0.0:8000 -w 1 -k uvicorn.workers.UvicornWorker --certfile=/opt/SUBWATCH/cert/cert.pem --keyfile=/opt/SUBWATCH/cert/privkey.pem --ca-certs=/opt/SUBWATCH/cert/chain.pem --daemon
#gunicorn --chdir /opt/SUBWATCH/api main:app -b 0.0.0.0:8000 -w 1 -k uvicorn.workers.UvicornWorker --certfile=/opt/SUBWATCH/cert/cert.pem --keyfile=/opt/SUBWATCH/cert/privkey.pem --ca-certs=/opt/SUBWATCH/cert/chain.pem --daemon
