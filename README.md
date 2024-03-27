# Electromagnetic Stimulation Platform

This repository contains the code and documentation for the stimulation controller used in the paper [Bioelectromagnetic Platform for Cell, Tissue, and In Vivo Stimulation](https://example.comhttps://www.mdpi.com/2079-6374/11/8/248).

![Image Description](./images/graphical_abstract.png)

# Documentation

Detailed documentation of both the coils and stimulation controller can be found in the manuals in the docs folder.

Additionally, the following three figures show the use cases, physical and electromagnetic properties, and the assembled coils and stimulation controller.

![Image Description](./images/simulated_coil_holders.png)
![Image Description](./images/magnetic_field_simulations.png)
![Image Description](./images/assembled_coils.png)

# Initial Setup

## ELEGOO Nano Setup

To get started, first install the [ELEGOO Nano driver](http://69.195.111.207/tutorial-download/?t=Nano3.0+)

Next, configure the ELEGOO Nano to communicate with the host PC's python application. Load the `prototype.ino` sketch from the [Arduino-Python3-Command-API github repository](https://github.com/mkals/Arduino-Python3-Command-API) to the ELEGOO Nano using the Arduino IDE or some other microcontroller programmer.

## Environment

Install virtualenv for creating virtual python environments. Then create and activate an environment.

### Windows (command prompt)

Install virtualenv:

`> python -m pip install virtualenv`

Create an environment: 

`> python -m venv env_location\controller`

Activate the environment:

`> env_location\Scripts\activate.bat`

### Linux

Install virtualenv:

`$ python3 -m pip install virtualenv`

Create an environment: 

`virtualenv controller`

Activate the environment:

`source env_location/stim_controller/bin/activate`

### Python Environment

Install the python package dependencies either manually or automatically using the `requirements.txt` file.

Automatic:

`pip3 install -r ./requirements.txt`

Manually:

`pip3 install pyserial arduino-python3 pyside2 pyqtgraph keyboard PyInstaller`

# Running the stimulation controller

Simply run the `stimulation_controller.py` python script when the stimulation controller is plugged in to the host computer to launch the GUI.

## Windows (command prompt)

`> python stimulation_controller.py`

## Linux

`$ python3 stimulation_controller.py`

## Bundling program into a single package

Use PyInstaller to bundle all of the necessary files into a single folder or executable so that it can be easily installed on a computer without configuring and setting up a Python environment. This reduces setup time for computers that simply need to use the stimulation controller, but otherwise do not need to do any development.

Navigate to the stimulation-controller folder:

`cd path/to/stimulation-controller/`

Run PyInstaller to bundle the application

`pyinstaller stimulation_controller.py`

Run the program from bundled package:

### Windows:

`C:\path\to\stimulation-controller\Windows\dist\stimulation_controller\stimulation_controller.exe`

### CentOS:

`/path/to/stimulation-controller/CentOs/dist/stimulation_controller/stimulation_controller`

# Cite
```
@article{ashbaugh2021bioelectromagnetic,
  title={Bioelectromagnetic platform for cell, tissue, and in vivo stimulation},
  author={Ashbaugh, Ryan C and Udpa, Lalita and Israeli, Ron R and Gilad, Assaf A and Pelled, Galit},
  journal={Biosensors},
  volume={11},
  number={8},
  pages={248},
  year={2021},
  publisher={MDPI}
}
```