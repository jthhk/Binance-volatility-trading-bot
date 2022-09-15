FROM python:3.9
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
ADD . ./
EXPOSE 8501 6379
ENTRYPOINT ["./docker/docker_entrypoint.sh"]
CMD ["python","./Binance_Detect_Mooningsv2.py"]
