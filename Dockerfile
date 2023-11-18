FROM python:3.10

# create venv
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENV FLASK_APP=vmon
ENV FLASK_ENV=production
ENV DATABASE_URL="postgresql://username:password/instance"
ENV REDIS_URL="redis://redis:6379/0"

# create a group and user
RUN groupadd -g 1000 vmon && useradd --no-create-home -r -u 1000 -g vmon vmon

# copy requirements.txt
COPY /requirements.txt /

# upgrade pip, install wheel and requirements

RUN pip install --upgrade pip
RUN pip install wheel
RUN pip install -r requirements.txt

# SETUP TINI
ENV TINI_VERSION v0.19.0
RUN curl -L https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini -o /tini
RUN chmod +x /tini

# copy every content to the image
COPY --chown=vmon:vmon /vmon /vmon

# change user
USER vmon

# expose listening port
EXPOSE 5000

#set entrypoint
CMD ["gunicorn", "--chdir", "vmon", "--bind", "0.0.0.0:5000", "vmonFactory:create_app()", "--workers", "1", "--threads", "5"]
