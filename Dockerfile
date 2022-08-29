FROM alpine:3.16.2

# add mono repo and mono
RUN apk add --no-cache mono --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing

# install requirements
RUN  apk add --no-cache --upgrade ffmpeg mediainfo python3 git py3-pip python3-dev g++ cargo mktorrent
RUN pip3 install -U wheel

# clone repo, install reqs
RUN git clone https://github.com/L4GSP1KE/Upload-Assistant.git
RUN pip3 install -U -r /Upload-Assistant/requirements.txt

ENTRYPOINT ["python3", "/Upload-Assistant/upload.py"]
