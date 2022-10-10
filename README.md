# About

When automatic subject indexing methods (multi-label classification) are applied 
on big and diverse data sets, the quality of indexing can be impaired by different factors. 
As a consequence, quality is typically controlled before using automatically generated information 
in operative information retrieval systems.
The releasetool intends to assist libraries in such quality control workflows.

```
+---------+          +-----------------------+
|automatic|          |  releasetool          |
|subject  +--------->+  (quality assessment) |
|indexing | import   |                       |
+---+-----+ release  +----------+------------+
    ^       candidate           | 
    |                           |
    | documents                 | if quality == ok:
    | without                   |   release controlled subject terms
    | controlled                v
    | subject terms    +--------+--------+
    +------------------+ library catalog |
                       | (used for IR)   |
                       +-----------------+
```

The project aims to build a straight-forward web application as a starting point 
for quality assessment of automatic subject indexing.
The intended audience of this project are software developers at libraries 
as well as librarians involved in automatic subject indexing projects.

Here you can find the current _development version_.
A prototype of the tool has been presented under the title
[Towards Semantic Quality Control of Automatic Subject Indexing](http://dx.doi.org/doi:10.1007/978-3-319-67008-9_56)
(Martin Toepfer &amp; Christin Seifert, 2017)
at TPDL-2017, Thessaloniki, Greece, September 18-21, 2017.
That predecessor used semantic web technology as a database backend.
By contrast to the prototype, the new releasetool has been reimplemented and revised 
substantially in several aspects.
Semantic web technology is now only utilized as a service to access the thesaurus.
The reimplementation has been performed in order to put more emphasize on business processes
and system integration.

The releasetool is a project of ZBW's automatic subject indexing working group.
It has been written by [Martin Toepfer](https://www.zbw.eu/de/forschung/science-2-0/martin-toepfer/), 2017-2018.
Please visit [our website](https://www.zbw.eu/en/about-us/key-activities/metadata-generation/) for more information.

[ZBW -- Leibniz Information Centre for Economics](https://www.zbw.eu)

# Notes

The releasetool has been developed for the ZBW,
hence testing and application yet focused on economics and the STW.
Interfaces and configuration options are, however, implemented to apply the tool in different domains.

The code has not yet reached a stable state and coding style has been handled tolerantly.

# Features

In a nutshell:

* __review__:
    * assess quality at the document-level (complete topic representation)
    * assess quality at the subject-level (give feedback for each single suggested subject)
    * add missing subjects, using auto-suggest lists based on your thesaurus
* __monitor__ and maintain (admin):
    * upload automatic subject indexing results (release candidate files)
    * compare reviews
    * create new collections
* __explain__:
    * analyse errors, have a look at which method suggested a specific subject and how confident it was

Several operations for release processes are supported with basic default implementations,
which can be customized.
Some import/export features are implemented, 
so that you can use your favorite tools, like for example [R](https://www.r-project.org/) 
or standard office software suites, 
to create more complex samples with fine-grained control, 
and then import the samples as collections easily via the *admin interface* or 
at the command line using [commands](zaptain_rt_app/management/commands/).

# DOCUMENTATION

* [Technical documentation](docs/README_DEV.md)
* User documentation for the two main types of users:
  * [PROSIs](docs/README_PROSI.md) (professional subject indexers) mainly perform reviews,
  * [LISUs](docs/README_LISU.md) (librarian super users) manage and monitor releases.

## How to run
The easiest way to run releasetool is via docker.
1. Check out the repository.
2. Copy `zaptain_ui/settings_template.py` to `zaptain_ui/settings_local.py` and adjust the File to your needs.
Especially change the `SECRET_KEY` variable and remove the line below it.
One possibility to create a secret is `< /dev/urandom tr -dc _A-Z-a-z-0-9 | head -c${1:-64};echo;`.
The database file is defined in the `DATABASES` setting.
 The database file should be placed somewhere in `/rt_data` (because this folder is created in the Dockerfile for that purpose). E.g.
```
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/rt_data/rt_v1alpha.sqlite',
    }
}
```
The release candidates are placed in `$MEDIA_ROOT/releasecandidates`. `MEDIA_ROOT` should be a relative path to `/releasetool` , e.g. `MEDIA_ROOT=rt_data` .
3. Run `docker build -t rt .` from inside the base directory of this repository.
4. Run `docker run -it --rm -p 8085:8000 rt`.
To persists the data use [docker volumes](https://docs.docker.com/storage/volumes/).
`/rt_data` should be bound to a local folder in order to persist the database.
`/releasetool/$MEDIA_ROOT/` should be bound to a local folder in order to persist the release candidates.
It should be bound to a local folder.
Furthermore you should [expose](https://docs.docker.com/engine/reference/commandline/run/#publish-or-expose-port--p---expose) port 8000 of the container.
5. Access the UI in a browser at `http://<your_host>:<port_defined_above>/releasetool`
6. Login using the credentials `rtadmin` with password `changeme`.
7. Click on `Admin` in the upper right corner.
8. Change the password. This functionality is again available in the upper right corner.
9. Inside the admin view select `Rt configs`
10. Now change all available keys to your desired values.
This can be done by clicking on them, then hit `SAVE` in the lower left corner.

|Key   | Description | Example|
|------|------------:|-------:|
catalog API pattern|  URL where the tool can get metadata from. Needs to be parametrized with `{docid}. |`https://api.econbiz.de/v1/{docid}
document weblink pattern| URL  where the user can access the publication. Needs to be parametrized with `{docid}`| https://www.econbiz.de/Record/{docid}
name of the main automatic indexing method| Name of the indexing method that has generated the suggestions. This needs to be the same as the one you set for your imported collcection.| zaptain-rules
support email|Email where users can reach support | someone@domain.org
thesaurus category type| Type for thesausurus category. Used to structure the graph view.|http://zbw.eu/namespaces/zbw-extensions/Thsys
thesaurus descriptor type| Type for thesaurus concepts. |http://zbw.eu/namespaces/zbw-extensions/Descriptor
thesaurus sparql endpoint| URL where the thesaurus can be queried using SPARQL| http://zbw.eu/beta/sparql/stw/query
thesaurus sparql query  |Not used | |

# Context Information
This code was created as part of the subject indexing automatization effort at [ZBW - Leibniz Information Centre for Economics](https://www.zbw.eu/en/).r
 See [our homepage](https://www.zbw.eu/en/about-us/key-activities/automated-subject-indexing) for more information, publications, and contact details.
The releasetool has been created by Martin Toepfer, 2017–2018.
