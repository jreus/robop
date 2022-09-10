# Robot Opera TTS to RAVE Tool

run using `python tts-rave.py`

Note: Because the tts-rave.py tool runs non-realtime, your audio settings don't matter.
Normally realtime RAVE clients (PureData, SuperCollider, VST, etc..) must always be run with audio settings of 48000khz / 2048 block size

## Usage
A prompt will appear once the app has loaded, anything you type will be synthesized via espeak into a wav file and then processed through the currently selected rave model. A few special commands are provided which will not be spoken:

```
help        show the app help text

quit        quit the app

voices      list all available espeak voices on your system

voices=en   list all espeak voices for a given language (in this case 'en')

set         set the value of one or more synthesis parameters
```

The available parameters are:

```
speed=100           speed in words per minute: default is 175

gap=10              word gap in units of 10ms at default speed: default is 10

pitch=70            pitch: 0-99, default is 50

amp=170             amplitude: 0-200, default is 100

voice=mb/mb-pl1     an espeak voice (see 'voices')

model=human         RAVE model: 'human' 'machine' 'humanmachine' or 'humanmachine_noft'

playraw=True        Play raw TTS audio: 'True' or 'False'

playrave=False      Play RAVE audio: 'True' or 'False'

debug=True          Show debugging output: 'True' or 'False'
```

Example commands:

List all English espeak voices
> voices=en

Change the current RAVE model to humanmachine_noft
> set model=humanmachine_noft

Play only the TTS voice and not the RAVE voice
> set playraw=True playrave=False

Set the pitch, amplitude, word gap, and speed of the espeak voice.
> set pitch=80 amp=100 gap=1 speed=70 model=human

Change the espeak voice to Polish
> set voice=mb/mb-pl1



# ENVIRONMENT SETUP (Tested on Ubuntu 20.04)

The TTS-RAVE tool was developed with a miniconda environment.
Setting up conda is probably the easiest way to get it running.

## Where to put RAVE models

The TTS-RAVE tool is expecting to find each of the RAVE models in a directory called `models`
in the parent directory of this repository. Your file structure should look something like this:

```
Parent Directory/
  models/
    human01rt/
    - 2M83.ckpt
    machine01rt/
    - 2M81.ckpt
    humanmachine01rt/
    - 4M1.ckpt
    - 3M_nofinetuning.ckpt
  robop/ (this repository!)
```


## The Short Way

If you're using Ubuntu 20.04 like I am, then you might be lucky and only need to use the provided conda `environment.yml` file to create your local conda environment.

__Note:__ I haven't tried creating the environment from this file myself. I have only exported the spec file using the command `conda env export > environment.yml`.

To use the this file to create an identical environment on the same machine or another machine:
```
conda create --file robop_env.yml
```

To use the spec file to install its listed packages into an existing environment:
```
conda install --name myenv --file robop_env.yml
```



## The Long Way (probably what you will need to do)

The long way for setting up your environment is to install all the dependencies manually so that they are sure to work on your system configuration.

First make sure conda (anaconda or miniconda) is installed on your system.

You will also need to install (espeak)[https://github.com/espeak-ng/espeak-ng] - the open source TTS project. I'm not sure how to do this on Mac, though (MacPorts)[https://ports.macports.org/port/espeak-ng/] seem to offer one option.

On Ubuntu Linux this is easy to do by using `apt-get`.
e.g.
```
sudo apt-get update
sudo apt-get install espeak-ng
```

Install More MBROLA Voices (optional but recommended)
```
sudo apt-get install mbrola-*
```

Create a new conda environment with python 3.9
```
conda update conda
conda create -n robop python=3.9
conda activate robop
```

Install pytorch according to your system configuration. See: https://pytorch.org/get-started/locally/

For my system this was the recommended install command (yours may be different)
```
conda install pytorch torchvision torchaudio cudatoolkit=11.6 -c pytorch -c conda-forge
```

Install other dependencies needed by RAVE and the TTS-RAVE tool.
```
conda install scipy scikit-learn numpy matplotlib
conda install pyaudio
conda install -c conda-forge librosa python-sounddevice
conda install -c conda-forge einops tqdm gputil
```

Get RAVE via git.
```
git clone https://github.com/acids-ircam/RAVE.git
cd RAVE
```

Install RAVE
NOTE: Before running `pip install`, first modify `requirements.txt` by replacing `==` with `>=` for librosa, numpy, tqdm, einops and torch.
```
pip install -r requirements.txt
```

Finally, run the follow line to add RAVE to your PYTHONPATH so that the TTS-RAVE tool can import it. You will probably want to add this to .bash_aliases or .bashrc so that it gets run automatically.
```
export PYTHONPATH="${PYTHONPATH}:/absolute/path/to/RAVE"
```
