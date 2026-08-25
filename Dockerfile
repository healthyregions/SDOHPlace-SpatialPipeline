FROM --platform=linux/amd64 public.ecr.aws/lambda/python:3.12

WORKDIR ${LAMBDA_TASK_ROOT}

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY sdohplace_spatial ./sdohplace_spatial

CMD ["sdohplace_spatial.handler.lambda_handler"]
