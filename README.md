# NiceHash Afterburner automatic profile switcher

- [Introduction](#introduction)
- [Rationale](#rationale)
- [Setup](#setup)
- [How to run](#run)
- [Acknowledgments](#Acknowledgments)


# <a name="introduction"></a>Introduction
Script used to detect a change in mining algorithm and adjust MSI afterburner profile to maximize profits. Profile is reverted if Excavator is no longer running.<br />
<br />
<img src="Resources/NHAPS Screenshot.png" />

Script tested with:<br />
NiceHash Miner version 3.0.5.6<br />
Excavator version 1.6.2a<br />
MSI Afterburner 4.6.2<br />
Python version 3.9.0 64-bit<br />
Windows 10 20H2<br />
<br />
.exe complied with:<br />
PyInstaller<br />


# <a name="rationale"></a> Rationale
The python script checks queries the local Excavator API for the current algorithm's ID number, which is then compared to the previous ID. If the script identifies a change in mining algorithm, a second check is run to determine which MSI Afterburner profile that should be run and switches to the said profile if necessary.

Basically: low power profile if daggerhashimoto is running else high power profile.


**Running MSI Afterburner without UAC prompts**

For this script to operate, MSI Afterburner must be running. However, without elevated privilges, each time the program switches profiles the user is prompted to allow the program to make changes. Having to click yes every time the script switches algorithms would ruin the automatic nature of the program. </br >

To circumvent the UAC prompt there are two options:
1. Turn off UAC completely (NOT recommended)
2. Use Task Scheduler to run MSI Afterburner profile changes with elevated privileges


# <a name="setup"></a> Setup
## Run as admin
Or
## Use Task Scheduler to launch MSI Afterburner without a UAC prompt
To accomplish this I followed a guide by digitalcitizen
[How To Use The Task Scheduler To Launch Programs Without UAC Prompts](https://www.digitalcitizen.life/use-task-scheduler-launch-programs-without-uac-prompts)

The task names can be configured in config.ini under low_power_profile_name and high_power_profile_name.

**Action Triggers are set to**<br />
[low_power_profile_name]<br />
Action: Start a program<br />
Program/script: "C:\Program Files (x86)\MSI Afterburner\MSIAfterburner.exe"<br />
Add arguments (optional): -Profile1<br />
<br />
[high_power_profile_name]<br />
Action: Start a program<br />
Program/script: "C:\Program Files (x86)\MSI Afterburner\MSIAfterburner.exe"<br />
Add arguments (optional): -Profile2<br />


# <a name="run"></a> How to run?
The .exe can be run with administrator privileges, or after setting up the two actions through Task Scheduler, the .exe can be run as normal. The software must be run locally. It is possible to run the python script directly using Python 3.

# <a name="Acknowledgments"></a> Acknowledgments
GitHub User [YoRyan](https://github.com/YoRyan) - code used to read excavator API over TCP
