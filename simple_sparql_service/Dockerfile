FROM python:3.11.0a3-alpine3.15
RUN pip install  --no-cache-dir flask waitress rdflib
ADD sparql.py sparql.py
CMD python3 sparql.py -p 5000 -f /rdf.xml
