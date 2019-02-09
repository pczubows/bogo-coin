FROM python:3.7.2-alpine

WORKDIR bogo-coin

COPY requirements.txt /bogo-coin/
COPY coin /bogo-coin/blockchain
COPY app/ /bogo-coin/app 

RUN ls -la /bogo-coin
RUN cd /bogo-coin && pip install -r requirements.txt

EXPOSE 5000

ENV PYTHONPATH "${PYTHONPATH}:/bogo-coin:/bogo-coin/blockchain"

CMD ["python", "app/app.py"]