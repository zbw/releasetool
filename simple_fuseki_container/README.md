# Simple Fuseki Service
This folder provides a Docker container for running a local Fuseki instance.
It is aimed at providing a SPQRQL endpoint for use with the release tool.
The current configuration will create a graph called `stw` available in Fuseki.
If you want to change this, you need to modify two files:
### `assembler.ttl`
```
    fuseki:name              "stw" ;   # http://host:port/stw
```
### `fuseki.ttl`
```
   fuseki:name              "stw" ;   # http://host:port/stw
```

## Create the Container
To build the container you need a SKOS vocabulary, placed in this folder called `skos.rdf`.
Run `docker build --rm -t simple_fuseki .` while inside this directory to build the container.

## Run the Container
After the container is built you can run the container by executing
`docker run -v $PATH_TO_SKOS_FILE:/rdf.xml simple_fuseki`,
where `$PATH_TO_SKOS_FILE` is the location of your skos file.


# Running with Releasetool
To run the Fuseki as a service for the releasetool docker compose can be used.
In order to do so you need to build the individual images first.
Then you need to create two folders.
One for release tool media and data respectively.
Then you need to add the folders to the `docker-compose.yml` file.
This is important as the default points to the `/tmp` directory,
i.e., you will loose your data after a reboot.
The mount points inside the container have to match the `MEDIA_ROOT` variable of the `settings_local.py` file.
Then inside the folder containing this readme run `docker-compose up`.
Open the browser and go to "127.0.0.1:8085/releasetool".
If you run it on a remote machine you have to change the address accordingly.
