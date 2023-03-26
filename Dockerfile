FROM alpine:latest

# add mono repo and mono
RUN apk add --no-cache mono --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing

# install requirements
RUN apk add --no-cache --upgrade ffmpeg mediainfo python3 git py3-pip python3-dev g++ cargo rust make
RUN pip3 install wheel

# Compile mktorrent with pthreads instead of using packaged version (that doesn't HAVE PTHREADS!)
RUN cd /tmp && git clone https://github.com/pobrn/mktorrent.git && cd mktorrent && git checkout tags/v1.1 && USE_PTHREADS=1 make install && cd /tmp && rm -Rfv mktorrent

WORKDIR Upload-Assistant

# install reqs
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# copy everything
COPY . .

ENTRYPOINT ["python3", "/Upload-Assistant/upload.py"]
