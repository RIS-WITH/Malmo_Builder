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

3. export malmo schemas
Add ```export MALMO_XSD_PATH=~/MalmoPlatform/Schemas``` (or your Schemas location) to your ```~/.bashrc``` and then ```source ~/.bashrc```

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

1. clone the project in the MamloPlatform repository

2. navigate to Malmo_Builder

3. run malmo_builder in the terminal 
experimental version (takes time to load):
```sh 
./malmo_builder_run.sh
```
manual version:
three steps
- run three clients
```sh
cd ../Minecraft
./launchClient.sh
```
- change the last opened client which will be at 10002 to port 10000 and the first one to 10002 using GUI
First change the client 10000 to 10002 on minecraft GUI (malmo wont like it but will change it later)
ESC > mods > malmo > settings > port > 10002 > done
Then change the client 10002 to 10000 on minecraft GUI
ESC > mods > malmo > settings > port > 10000 > done
now to solve malmo problem with first change, 10002 to 0
ESC > mods > malmo > settings > port > 0 > done

- run the main python file in the malmo_builder directory
```sh
python3 main.py
```


