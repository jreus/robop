import os, sys
import random
from pathlib import Path
import logging
from logging import Logger
from typing import List, Union, Any, Dict

import soundfile
import pydub
from pydub.playback import play
from time import sleep
import re
import librosa
import torch
from rave import RAVE
torch.set_grad_enabled(False) # we're only doing inference


class silence_stdout:
    """
    swallow all stderr and stdout
    adapted from: https://stackoverflow.com/questions/11130156/
    """
    def __init__(self):
        # Open a pair of null files
        self.null_fds = [os.open(os.devnull, os.O_RDWR) for x in range(2)]
        # Save the actual stdout (1) and stderr (2) file descriptors.
        self.save_fds = [os.dup(1), os.dup(2)]

    def __enter__(self) -> None:
        # Assign the null pointers to stdout and stderr.
        os.dup2(self.null_fds[0], 1)
        os.dup2(self.null_fds[1], 2)
        return None

    def __exit__(self, *_):
        # Re-assign the real stdout/stderr back to (1) and (2)
        os.dup2(self.save_fds[0], 1)
        os.dup2(self.save_fds[1], 2)
        # Close all file descriptors
        for fd in self.null_fds + self.save_fds:
            os.close(fd)


class Robop:
    def __init__(self, audio_write_path: str, use_cuda: bool, logger: Logger) -> None:
        self.audio_write_path = Path(audio_write_path)
        self.use_cuda = use_cuda
        self.log = logger

        self.run_repl = True
        self.fidx = 0
        self.speed = 175 # speed in words per minute, default is 175
        self.gap = 10 # word gap in units of 10ms at default speed
        self.pitch = 50 # pitch adjustment 0-99, default is 50
        self.amp = 100 # amplitude up to 0-200, default is 100
        self.voice = "mb/mb-us1"
        self.model = "human"
        self.playraw = False
        self.playrave = True

        # Create audio write dir if does not exist...
        if self.audio_write_path.suffix != '':
            self.audio_write_path = self.audio_write_path.parent
            self.log.warning(f"Got audio scratch path as a file, using: {self.audio_write_path}")

        if not self.audio_write_path.exists():
            self.log.warning(f"Audio scratch path does not exist, creating: {self.audio_write_path}")
            os.makedirs(self.audio_write_path)

    def load_models(self, model_specs: dict) -> None:
        """
        Instantiate RAVE models from a model specs dict.
            model_specs     A dict of model specs, see example code below for format
        """

        if 'rave' in model_specs:
            rave_model_specs = model_specs['rave']
            rave_model_root = model_specs['rave_root_path']
        else:
            rave_model_specs = dict()
            rave_model_root = None

        self.rave = dict()
        for modelname, spec in rave_model_specs.items():
            model_path = os.path.join(rave_model_root, spec[0])
            model_sr = spec[1]
            realtime = (os.path.splitext(model_path)[1] == ".ts")
            model_delay = spec[2]

            self.rave[modelname] = dict()
            self.rave[modelname]["realtime"] = realtime
            self.rave[modelname]["delay"] = model_delay
            self.rave[modelname]["sr"] = model_sr

            # Load model
            self.log.info(f"LOADING MODEL at {spec}")
            if realtime:
                self.rave[modelname]['model'] = torch.jit.load(model_path).eval()
            else:
                self.rave[modelname]['model'] = RAVE.load_from_checkpoint(model_path, strict=False).eval()

    def rave_generate(self, input_file: str, file_sr: int, use_models: list):
        """
        Synthesize RAVE outputs for the given RAVE model ids on an input file.

        input_file  audio filepath to process using RAVE
        file_sr     sample rate of input_file
        use_models  list of model ids to render, if None then uses all available models
        """
        filepath = Path(input_file)
        x, sr = librosa.load(filepath, sr=file_sr)

        x = torch.from_numpy(x).reshape(1,1,-1).float()
        savepaths = []

        if use_models is None:
            use_models = self.rave.keys()

        for modelname in use_models:
            model = self.rave[modelname]
            latent = model['model'].encode(x)
            y = model['model'].decode(latent)
            wav = y.reshape(-1).numpy()
            if model['delay'] > 0:
                # Makeup for delay offset
                remove_samples = int(model['sr'] * model['delay'])
                wav[0:-remove_samples] = wav[remove_samples:] # shift samples from remove_samples to beginning
                wav[-remove_samples:] = 0.0 # silence end of signal..
            savepath = os.path.abspath(os.path.join(self.audio_write_path, f"{filepath.stem}_rave_{modelname}.wav"))
            soundfile.write(savepath, wav, sr)
            self.log.info(f"Wrote file: {savepath}")
            savepaths.append(savepath)
        return savepaths

    def print_help(self) -> None:
        helpmsg = """Enter text to speak.
        Type help to show this help text
        Type quit to exit
        Type voices to list all espeak voices on your system
        Type voices=en to list all espeak voices for a given language (in this case 'en')
        Type set followed by a parameter assignment to set values
            example:
            set pitch=80 amp=100 gap=1 speed=70 model=human


        speed=175        # speed in words per minute, default is 175
        gap=10           # word gap in units of 10ms at default speed
        pitch=50         # pitch adjustment 0-99, default is 50
        amp=100          # amplitude up to 0-200, default is 100
        voice=gmw/en     # an espeak voice
        model=human      # RAVE model - human, machine, humanmachine
        playraw=True     # Play raw TTS audio
        playrave=False   # Play RAVE audio
        """
        print(helpmsg)

    def process_commands(self, input: str) -> str:
        """
        Process any inline commands in a user input.

        Returns a string with all commands removed, or none if only whitespace remains.
        """

        if input == 'help':
            self.print_help()
            input = None
        elif input == 'quit' or input == 'exit':
            self.run_repl = False
            input = None
        elif input[:6] == 'voices':
            rx = re.compile(r'voices\=([A-Za-z\\\-0-9]+)')
            m = rx.search(input)
            if m is None:
                os.system('espeak --voices')
            else:
                lang = str(m.group(1))
                os.system(f'espeak --voices={lang}')
            input = None
        elif input[:3] == 'set':
            rx = re.compile(r'( ([a-z]+)\=([A-Za-z\\\-0-9]+))')
            m = rx.findall(input)
            if len(m) > 0:
                for cmd in m:
                    param = str(cmd[1])
                    val = cmd[2]
                    if param in ['speed', 'pitch', 'amp', 'gap']:
                        val = int(val)
                        exec(f"robo.{param} = {val}")
                        print(f"Set{cmd[0]}")
                    elif param in ["model", "voice"]:
                        val = str(val)
                        exec(f"robo.{param} = '{val}'")
                        print(f"Set{cmd[0]}")
                    elif param in ["playraw", "playrave"]:
                        val = bool(val)
                        exec(f"robo.{param} = {val}")
                        print(f"Set{cmd[0]}")
                    else:
                        exec(f"Error: Undefined parameter '{param}'")
            else:
                print(f"Error: set must be followed by a series of parameter value assignments.")
            input = None

        return input

    def generate_voice(self, text: str) -> None:
        result = {"text": text, "msg": 'generated_wavset'}

        filename = f'tts_raw{self.fidx}.wav'
        filepath = os.path.join(self.audio_write_path, filename)
        cmd = f'espeak -s {self.speed} -g {self.gap} -p {self.pitch} -a {self.amp} -v {self.voice} -w "{filepath}" "{text}"'
        self.log.debug("RUN:"+cmd)
        os.system(cmd)
        sleep(0.1)
        result['filepath']=filepath
        self.fidx += 1

        if self.playraw:
            wav = pydub.AudioSegment.from_file(filepath, format="wav")
            with silence_stdout():
                play(wav)

        if self.playrave:
            res = self.rave_generate(filepath, file_sr=48000, use_models=[self.model])
            self.log.debug(res)
            ravwav = pydub.AudioSegment.from_file(res[0], format="wav")
            with silence_stdout():
                play(ravwav)
            result['rave_output'] = res

        return result


    def run_chat_repl(self):
        print(f"Type help for help")
        while self.run_repl:
            try:
                recv = input('> ')
                self.log.debug(f"Got:{recv}")
                text = self.process_commands(recv)
                if text is not None:
                    self.generate_voice(text)

            except(KeyboardInterrupt, EOFError, SystemExit) as e:
                print("Exit Robop...")
                break



if __name__ == '__main__':
    import argparse
    from argparse import RawTextHelpFormatter

    parser = argparse.ArgumentParser(
        description="""ROBOP Voice Synthesizer\n\n""",
        formatter_class=RawTextHelpFormatter,
    )

    parser.add_argument(
        "--debug_level", "-d",
        type=str,
        default="INFO",
        help="Debug level, one of DEBUG INFO WARNING ERROR",
    )

    parser.add_argument(
        "--temp_path", "-o",
        type=str,
        default="tmp/wav",
        help="Audio write / temp directory.",
    )

    parser.add_argument("--use-cuda", type=bool, help="Run model on CUDA.", default=False)


    args = parser.parse_args()

    audio_write_path = Path(args.temp_path).absolute()
    use_cuda = args.use_cuda
    log_level = eval(f"logging.{args.debug_level}")
    logging.basicConfig(level=logging.WARNING)
    log = logging.getLogger('ROBOP')
    log.propagate = False
    log.setLevel(log_level)

    robo = Robop(
        audio_write_path,
        use_cuda,
        logger=log
    )

    model_specs = {
        'rave_root_path': os.path.abspath("../models/"),
        'rave': {
            "human": [
                "human01rt/2M83.ckpt",
                48000,
                0,
            ],
            "machine": [
                "machine01rt/2M81.ckpt",
                48000,
                0,
            ],
            "humanmachine": [
                "humanmachine01rt/4M1.ckpt",
                48000,
                0,
            ],
        }
    }

    robo.load_models(model_specs)
    robo.run_chat_repl()
