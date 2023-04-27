FROM debian:bullseye

RUN apt update && apt install -y python3-dev python3-pip python3-venv

RUN python3 -m pip install -U --user ortools

COPY ./jobShop.py /main.py

CMD ["python3", "/main.py"]
