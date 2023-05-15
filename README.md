# Malmo Builder
a data collecting enviroment for HRI research


## Malmo Installation

How to install on ubuntu 18.04.6 LTS for other ways to install look at https://github.com/Microsoft/malmo/ 

1. Install the latest version of Malmo from https://github.com/Microsoft/malmo/releases

2. Install dependencies available from the standard repositories:
```sh
sudo apt-get install libboost-all-dev libpython3.5 openjdk-8-jdk ffmpeg python-tk python-imaging-tk

sudo update-ca-certificates

pip install Pillow
```
**notice:** if you have more than one version of java then you must select openjdk version "1.8.0_362" or launching will fail 
```sh
### List all java versions:

update-java-alternatives --list

### Set java version as default (needs root permissions):

sudo update-java-alternatives --set /path/to/java/version

### where /path/to/java/version is one of those listed by the previous command (e.g. /usr/lib/jvm/java-1.8.0-openjdk-amd64).
```

3. expoert malmo schemas
Add ```export MALMO_XSD_PATH=~/MalmoPlatform/Schemas``` (or your Schemas location) to your ```~/.bashrc``` and do ```source ~/.bashrc```

4. launch
```sh
cd Minecraft
./launchClient.sh 
```
**notice:** if you have a problem with opengl then you may try:
 - restarting your device
 - clean gardle

5. Launch an agent:
Running a Python agent:
```sh
cd Python_Examples
python3 run_mission.py
```
## Using Malmo Builder

1. clone the project in the MamloPlatform repositorie

2. launch 3 terminals and run in each one of them:
in the malmo platform repositorie:
```sh 
cd Minecraft
./launchClient.sh
```

3. navigate to Malmo_Builder

4. run in the terminal ```sh python3 main.py```
