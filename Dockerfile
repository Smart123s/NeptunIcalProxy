FROM python:3.13

COPY NeptunIcalProxy.py .

CMD ["python", "-u", "NeptunIcalProxy.py"]
