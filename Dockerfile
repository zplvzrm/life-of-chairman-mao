FROM python:3.11

LABEL name="life-of-chairman-mao"
LABEL version="0.1.0"
LABEL description="毛主席的一生。"

WORKDIR /app

ADD . ./

# CMD ["python"]