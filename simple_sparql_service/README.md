# Simple SPARQL Service
This folder provides a docker container for a simple SPARQL endpoint to use with the release tool while testing.
It is not intended for production use.
Build the container as follows:
```
docker build --rm -t simple_sparql .
```
Then run it using
``
docker run -u $(id -u):$(id -g) --rm -v $THESAURUS_FILE:/rdf.xml -p $PORT:5000 simple_sparql
```
where `$THESAURUS_FILE` is the path to the vocabulary in rdf/xml format and `$PORT` is the port you want to use on the host machine.
