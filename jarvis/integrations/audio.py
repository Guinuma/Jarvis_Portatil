"""Volume e saídas de áudio através da API do Windows."""
import re
from .editor import normalize


def audio_command(text):
    command = normalize(text).rstrip('.!?')
    volume = re.fullmatch(r'(?:define|altera|muda) (?:o )?volume (?:para )?(\d+)(?:%| por cento)?', command)
    output = re.fullmatch(r'muda (?:a )?saida de audio para (.+)', text, re.I)
    if output is None:
        output = re.fullmatch(r'muda (?:a )?saída de áudio para (.+)', text, re.I)
    if not volume and not output and command not in {'consulta o volume', 'mostra as saidas de audio'}:
        return None
    import comtypes
    from pycaw.pycaw import AudioUtilities
    from pycaw.constants import ERole
    comtypes.CoInitialize()
    try:
        if volume or command == 'consulta o volume':
            endpoint = AudioUtilities.GetSpeakers().EndpointVolume
            if volume:
                value = int(volume[1])
                if not 0 <= value <= 100:
                    raise ValueError('Escolhe um volume entre 0 e 100%.')
                endpoint.SetMasterVolumeLevelScalar(value / 100, None)
            return f'Volume do Windows: {round(endpoint.GetMasterVolumeLevelScalar() * 100)}%.'
        devices = AudioUtilities.GetAllDevices(data_flow=0, device_state=1)
        if output:
            name = output[1].strip().strip('"')
            matches = [d for d in devices if name == d.id or normalize(name) == normalize(d.FriendlyName)]
            if len(matches) != 1:
                return 'Escolhe uma saída ativa pelo identificador:\n' + '\n'.join(f'{d.FriendlyName}: {d.id}' for d in devices)
            device = matches[0]
            AudioUtilities.SetDefaultDevice(device.id, roles=[ERole.eConsole, ERole.eMultimedia])
            actual = AudioUtilities.GetSpeakers()
            if actual.id != device.id:
                raise OSError('O Windows não confirmou a mudança da saída de áudio.')
            return f'Saída de áudio do Windows: {actual.FriendlyName}.'
        return 'Saídas de áudio ativas:\n' + '\n'.join(f'{d.FriendlyName}: {d.id}' for d in devices)
    except comtypes.COMError as error:
        raise OSError('O Windows não conseguiu aceder ao dispositivo de áudio.') from error
    finally:
        comtypes.CoUninitialize()
