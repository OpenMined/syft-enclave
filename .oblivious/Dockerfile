WORKDIR /code

RUN apt-get update && \
    apt-get install -y git

COPY ./requirements.txt /code/requirements.txt
 
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
 
COPY ./src/ /code/
