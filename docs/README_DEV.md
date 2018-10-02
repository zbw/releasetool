# Technical Documentation

## Context and Requirements

**Infrastructure** (service oriented architecture):

```
+---------------+
|  releasetool  | request   +-----------------+
|  webapp       +----------^+   catalog-api   |
|               +v----------+                 |
|               | response  +-----------------+
|               |
|               |
|               | request   +-----------------+
|               +----------^+  thesaurus-api  |
|               +v----------+(SPARQL endpoint)|
|               | response  +-----------------+
+---------------+
```

API requirements:

* a __[Library catalog connetion](zaptain_rt_app/catalog_connection.py)__ to an API that conforms to the one used at [https://api.econbiz.de/v1](https://api.econbiz.de/).
* a __[thesaurus connection](zaptain_rt_app/thesaurus_conncetion.py)__ to an API that conforms to the one used at [http://zbw.eu/beta/sparql/stw/query](http://zbw.eu/beta/sparql/stw/query), see: [sparql-lab](http://zbw.eu/beta/sparql-lab/about/).
That is, you need to provide a SPARQL endpoint with [text search](https://jena.apache.org/documentation/query/text-query.html) support for your thesaurus that is represented in [SKOS](https://www.w3.org/TR/skos-reference/).

These services may be provided on different servers, possibly publicly available.

**Software (Server)**:

The releasetool requires python (Version >= 3.4) and the libraries specified in [requirements.txt](requirements.txt).
It has been tested on Windows 7 and on CentOS 7.5.

Please copy jquery 3.1.1, jquery-ui-1.12.1, bootstrap 3.3.7, and glyphicons into the corresponding locations (css, fonts, js)
in the `zaptain_rt_app/static/` folder.

**Software (Client)**:

* web browser: Firefox (60.1.0), javascript enabled

## Installation, Configuration, Customization

You should be familiar with the [django web framework (v2.0)](https://www.djangoproject.com/) and have satisfied all requirements.
The following steps guide you to a running development server.

In order to customize the releasetool, you have to set a few configuration options. 

Copy [zaptain_ui/settings_template.py](zaptain_ui/settings_template.py) to `zaptain_ui/settings_local.py`.
Set a new passphrase (SECRET_KEY) and absolute paths as described in that module, 
for instance, define the static files folder (STATIC_ROOT).
Create a superuser account etc.

In particular for testing, you can 
use the special manage command `rt_testdb` to reset the database to a specific test state.
You can further have a look at the
[test module's TestContentManager class](/zaptain_rt_app/tests.py).

You may want to start your development webapp now, and visit:

* [the admin site](http://127.0.0.1:8000/admin/zaptain_rt_app/rtconfig/), as well as,
* [the main page](http://127.0.0.1:8000/releasetool/)