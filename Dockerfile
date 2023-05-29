FROM debian:bullseye

RUN apt update && apt install -y python3-dev python3-pip python3-venv

RUN python3 -m pip install -U --user ortools grpcio-tools grpcio

COPY . .
RUN python3 -m grpc_tools.protoc -I./proto --python_out=. --pyi_out=. --grpc_python_out=. helloworld.proto

CMD ["python3", "/recipe.py"]
