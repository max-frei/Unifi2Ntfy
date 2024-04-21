FROM python:3.9-slim
ADD UnifiNtfy.py .
RUN pip install requests urllib3
CMD ["python", "./UnifiNtfy.py"] 