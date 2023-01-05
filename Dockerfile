FROM python:3.8 as base

# let's create a folder to work from 
WORKDIR /code

# copy over our requirements
COPY ./requirements.txt /code/requirements.txt

# install the python deps
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# copy over our source folder
COPY ./src/ /code/



FROM base as api-tests

# copy over tests
COPY ./tests/ /code/tests/

# install test requirements
RUN pip install -r /code/tests/requirements.txt

# run pytest
CMD ["python", "-m", "pytest", "tests/"]



FROM base as local-serve

# serve on local host
CMD ["python", "uvicorn_serve.py"]