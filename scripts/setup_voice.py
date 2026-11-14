"""Descarregar uma vez o modelo de voz para utilização sem Internet."""
from faster_whisper.utils import download_model
from jarvis.integrations.voice import model_path

if __name__ == '__main__':
    download_model('small', output_dir=str(model_path()))
    print(f'Modelo local preparado em {model_path()}')
