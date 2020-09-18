from python:3.8-slim
RUN pip install \
   'Django==3.1.*' \
   'django-import-export>=1.0.0' \
   'django-q == 1.3.*' \
   'simplejson>=3.11.1' \
   'urllib3>=1.21.1' \
   'requests>=2.18.4' \
   'numpy>=1.11.3' \
   'scipy>=0.17.1' \
   'pandas>=0.19.2'
RUN apt-get update
RUN apt-get install -y sqlite3
RUN mkdir /releasetool
RUN mkdir /rt_data
RUN mkdir /rt_static
WORKDIR /releasetool
ADD manage.py .
ADD zaptain_rt_app zaptain_rt_app
ADD zaptain_ui zaptain_ui
CMD sh -c 'python3 manage.py migrate && python3 manage.py runserver 0.0.0.0:8000'
