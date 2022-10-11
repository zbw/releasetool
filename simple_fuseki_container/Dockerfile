FROM tomcat:jdk17-openjdk-slim-bullseye

ENV FUSEKI_BASE /fuseki-base

# Fuseki installation
ENV FUSEKI_HOME /jena-fuseki

ENV JENA_HOME /jena
ENV JENA_BIN $JENA_HOME/bin

ENV CP "$FUSEKI_HOME/fuseki-server.jar:/javalibs/*"

ENV ASSEMBLER $FUSEKI_BASE/configuration/assembler.ttl
ENV CONFIG $FUSEKI_BASE/config.ttl

ENV SKOS_PTH /skos.rdf


RUN apt-get update && apt-get install -y tar curl
RUN curl -o apache-jena-fuseki-4.6.1.tar.gz https://dlcdn.apache.org/jena/binaries/apache-jena-fuseki-4.6.1.tar.gz \
        &&  tar -xzf apache-jena-fuseki-4.6.1.tar.gz
RUN cp -r apache-jena-fuseki-4.6.1 $FUSEKI_HOME
RUN curl -o apache-jena-4.6.1.tar.gz https://dlcdn.apache.org/jena/binaries/apache-jena-4.6.1.tar.gz \
        &&  tar -xzf apache-jena-4.6.1.tar.gz
RUN cp -r apache-jena-4.6.1 $JENA_HOME
COPY assembler.ttl $ASSEMBLER
COPY fuseki.ttl $CONFIG
RUN mkdir -p $FUSEKI_BASE/databases
ADD skos.rdf $SKOS_PTH
RUN /jena/bin/tdb1.xloader --loc=$FUSEKI_BASE/databases/tdb $SKOS_PTH
RUN java -cp $CP jena.textindexer --desc=$ASSEMBLER
WORKDIR /jena-fuseki
EXPOSE 3030
CMD ["java", "-cp", "*:/javalibs/*", "org.apache.jena.fuseki.cmd.FusekiCmd"]
