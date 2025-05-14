
FROM continuumio/miniconda3

WORKDIR /app

COPY environment.yml ./
RUN conda env create -f environment.yml \
    && conda clean -afy

SHELL ["conda", "run", "-n", "myenv", "/bin/bash", "-c"]

COPY . ./

WORKDIR /app/app

EXPOSE 8501


ENTRYPOINT [
  "streamlit", "run", "app.py",
  "--server.port", "8501",
  "--server.address", "0.0.0.0"
]