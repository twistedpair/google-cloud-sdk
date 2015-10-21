# Dockerfile for the python-compat runtime when user chooses env:2

FROM beta.gcr.io/google_appengine/python-compat-multicore

ADD . /app

RUN if [ -s requirements.txt ]; then pip install -r requirements.txt; fi
