# About

When automatic subject indexing methods (multi-label classification) are applied 
on big and diverse data sets, the quality of indexing can be impaired by different factors. 
As a consequence, quality is typically controlled before using automatically generated information 
in operative information retrieval systems.
The releasetool intends to assist libraries in such quality control workflows.

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
  * [PROSIs](README_PROSI.md) (professional subject indexers) mainly perform reviews,
  * [LISUs](README_LISU.md) (librarian super users) manage and monitor releases.







