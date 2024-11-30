FROM ubuntu:24.04

RUN apt update
RUN apt upgrade -y
RUN apt install -y pkg-config
RUN apt install -y gcc git cmake libssl-dev python3 python3-pip python3-venv python3-poetry pipx rustc cargo libffi-dev
RUN apt install -y zsh nano tmux

ENV PATH=$PATH:/root/.local/bin

EXPOSE	5555

WORKDIR /projects

RUN mkdir xcp-examples

RUN git clone https://github.com/christoph2/pyxcp
RUN git clone https://github.com/vectorgrp/xcplite

RUN cd pyxcp && \
    pipx install . && \
    pipx ensurepath && \
    cd .. && \
    ~/.local/bin/xcp-examples xcp-examples

COPY .tmux.conf /root/.tmux.conf
COPY .zshrc /root/.zshrc

COPY pyxcp_conf.py /projects/xcp-examples/pyxcp_conf.py

RUN cd xcplite/C_Demo && \
    cmake . && \
    cmake --build .

CMD ["/bin/zsh"]
