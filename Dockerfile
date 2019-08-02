FROM gcr.io/google_appengine/python

RUN virtualenv -p python3 /env
ENV PATH /env/bin:$PATH

ADD requirements.txt /app/requirements.txt
RUN /env/bin/pip install --upgrade pip && /env/bin/pip install -r /app/requirements.txt
ADD . /app
WORKDIR /app

EXPOSE 5000

CMD ["gunicorn", "-b", ":5000", "lsailor:create_app()"]