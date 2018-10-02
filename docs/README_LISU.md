__TODO__: this documentation is not yet finished

# SHOWCASE : STEPS

1. create indexer
1. import a release candidate
  1. import meta-data
1. create a collection
  1. sample randomly from release candidate
  1. sample randomly from specific journal/wp series
  1. import by CSV file etc.
1. review a collection
1. monitor progress, evaluate collection reviews
1. export

# USAGE

A general note:

There are two parts of the webapp:

* the main site `/releasetool` and its corresponding pages; depending on your user rights, you may have access to extende functionality.
* the admin site: `/releasetool/admin`.

## CREATE AN INDEXER

__TODO__

## IMPORT A RELEASE CANDIDATE

Precondition: You have already created a `INDEXER` model instance for this release candidate.

Import a releasecandidate CSV file at the admin site, see:

`/admin/zaptain_rt_app/releasecandidate/add/`

### IMPORT META-DATA

The release-candidate files do not contain meta-data such as 
titles, keywords, abstracts etc..

* This information is automatically gathered ad-hoc for the user interface
from infrastructure API services, if these are configured correctly.
* For full functionality, you can also load such information into the releasetool's
  database. You can do this either
  * through the admin site.
  * Alternatively, you can ask your technical staff to pre-load such information into the DB from a dump file using a custom script.


## CREATE A COLLECTION

You have different options:

1. custom approach, very flexible, requires some scripting/programming skills
1. default approach

### Custom Approach

for instance, import a collections file by csv, content:

`id,new collection,imported collection,"10010193380,10011392138,10011709724"`

at `/admin/zaptain_rt_app/collection/import/`

this solution bases upon:
https://django-import-export.readthedocs.io/en/latest/

### Default Approach

__TODO__

## REVIEW

see: [PROSI](README_PROSI.md)


## MONITOR

As an admin, go to `collection -> overview` 


## EXPORT

__TODO__

