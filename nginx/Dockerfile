FROM nginx:1.17

WORKDIR /usr/src/app

RUN rm /etc/nginx/nginx.conf
COPY ./nginx.conf /etc/nginx/
RUN rm /etc/nginx/conf.d/default.conf
COPY ./project.conf /etc/nginx/conf.d/

