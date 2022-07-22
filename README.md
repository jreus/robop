# Robot Opera Voice Tool

run using `python robop.py`


# Dependencies

Make sure `espeak` libraries are installed using `apt`.
e.g.
```
sudo apt-get update
sudo apt-get install espeak-ng

(( optional - install more mbrola voices ))
sudo apt-get install mbrola-*
```

```
conda update conda
conda create -n robop python=3.9
conda activate robop
```

Install python espeak wrapper
```
git clone https://github.com/nateshmbhat/pyttsx3.git
cd pyttsx3 && pip install .
```

Install pytorch according to your system configuration: https://pytorch.org/get-started/locally/
```
conda install pytorch torchvision torchaudio cudatoolkit=11.6 -c pytorch -c conda-forge
```

Install other dependencies
```
conda install scipy scikit-learn numpy matplotlib pyaudio
conda install -c conda-forge librosa einops tqdm gputil pydub

```

Install RAVE (modify requirements.txt with >= to allow the newer versions of librosa, numpy, tqdm, einops, torch)
```
git clone https://github.com/acids-ircam/RAVE.git
pip install -r requirements.txt
```

Add RAVE to your PYTHONPATH (add this to .bash_aliases for an easier time)
```
export PYTHONPATH="${PYTHONPATH}:/absolute/path/to/RAVE"
```
