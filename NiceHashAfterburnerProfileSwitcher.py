import time
import socket
import subprocess
import APIRequests
import psutil

import ctypes
import sys

from configparser import ConfigParser
from loguru import logger
from ast import literal_eval
from typing import Union
from NiceHashAlgoID import Dict as NiceHashAlgoIDs

config = ConfigParser()
config.read("config.ini")
logger.add('logs/profileSwitcher.log')


def check_process_running(executable_name: str) -> Union[bool, str]:
    """
    Checks if process is running.
    Args:
        executable_name: (str) The executable name.
    Returns:
        bool: True if excavator is running. False otherwise.
    """
    for proc in psutil.process_iter():
        try:
            # Check if process name contains the given name string.
            if executable_name.lower() in proc.name().lower():
                path = proc.exe()
                return path
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False


class ProfileSwitcher:
    def __init__(self, settings):
        self.version = "0.3"
        self.excavator_name = settings['excavator_executable_name']
        self.afterburner_name = settings['afterburner_executable_name']
        self.interval_time = literal_eval(settings['interval_time'])
        self.afterburner_path = settings['afterburner_application_path']
        self.excavator_address = (settings['excavator_ip'], int(settings['excavator_port']))
        self.wallpaper_engine_toggle = False
        self.wallpaper_engine_path = None
        self.wallpaper_engine_state = None

        self.low_power_profile = {
            'profile_num': settings['low_power_profile_num'],
            'profile_name': settings['low_power_profile_name']
        }
        self.high_power_profile = {
            'profile_num': settings['high_power_profile_num'],
            'profile_name': settings['high_power_profile_name']
        }

        self.previous_alg_id = None
        self.current_alg_id = None

        # Check for elevated privileges
        self.elevated_privileges = ctypes.windll.shell32.IsUserAnAdmin()

        # Check that MSIAfterburnerProfile1 and MSIAfterburnerProfile2 are found in task Scheduler
        if not self.elevated_privileges:
            try:
                subprocess.check_call([r"C:\Windows\System32\schtasks.exe", "/Query", "/TN",
                                       self.low_power_profile['profile_name']],
                                      shell=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                subprocess.check_call([r"C:\Windows\System32\schtasks.exe", "/Query", "/TN",
                                       self.high_power_profile['profile_name']],
                                      shell=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                self.scheduled_tasks_present = True
            except subprocess.CalledProcessError:
                self.scheduled_tasks_present = False
        # Check if Wallpaper Engine is running if flag is set
        if literal_eval(settings['wallpaper_engine']):
            w32 = check_process_running('wallpaper32')
            w64 = check_process_running('wallpaper64')
            if w32:
                self.wallpaper_engine_path = w32
                self.wallpaper_engine_toggle = True
            elif w64:
                self.wallpaper_engine_path = w64
                self.wallpaper_engine_toggle = True

    def switch_low_power_profile(self):
        """
        Switch MSI Afterburner to configured Low Power Profile
        """
        logger.info("Changing MSI Afterburner to Low Power Mode")
        if self.elevated_privileges:
            subprocess.Popen([self.afterburner_path, f"-profile{self.low_power_profile['profile_num']}"],
                             shell=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        elif self.scheduled_tasks_present:
            subprocess.Popen([r"C:\Windows\System32\schtasks.exe", "/RUN", "/TN",
                              self.low_power_profile['profile_name']],
                             shell=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def switch_high_power_profile(self):
        """
            Switch MSI Afterburner to configured High Power Profile
        """
        logger.info("Changing MSI Afterburner to High Power Mode")
        if self.elevated_privileges:
            subprocess.Popen([self.afterburner_path, f"-profile{self.high_power_profile['profile_num']}"],
                             shell=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        elif self.scheduled_tasks_present:
            subprocess.Popen([r"C:\Windows\System32\schtasks.exe", "/RUN", "/TN",
                              self.high_power_profile['profile_name']],
                             shell=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def pause_wallpaper_engine(self):
        """
        Pauses Wallpaper Engine
        """
        if self.wallpaper_engine_state != "paused":
            logger.info("Pausing Wallpaper Engine")
            subprocess.Popen([self.wallpaper_engine_path, "-control", "pause"],
                             shell=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            self.wallpaper_engine_state = "paused"

    def resume_wallpaper_engine(self):
        """
        Resumes Wallpaper Engine
        """
        if self.wallpaper_engine_state != "playing":
            logger.info("Pausing Wallpaper Engine")
            subprocess.Popen([self.wallpaper_engine_path, "-control", "play"],
                             shell=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            self.wallpaper_engine_state = "playing"

    def algo_monitor(self):
        """
        Main algorithm monitor loop.
        """
        logger.info(f"Starting Algorithm Monitor v{self.version}")

        if self.elevated_privileges:
            logger.info("Elevated privileges detected")
        elif self.scheduled_tasks_present:
            logger.info("Elevated privileges not detected but scheduled tasks present")
        else:
            logger.info("No elevated privileges or scheduled tasks detected, exiting...")
            time.sleep(1)
            sys.exit(0)
        if self.wallpaper_engine_toggle:
            logger.info("Wallpaper Engine detected, will pause while mining")
        # Main Loop
        while True:
            # localAPI
            if check_process_running(self.afterburner_name):
                if check_process_running(self.excavator_name):
                    try:
                        local_data = APIRequests.dict_from_tcp(self.excavator_address,
                                                               {"id": 1, "method": "algorithm.list", "params": []})
                    except socket.error as error:
                        logger.error(error)
                        logger.info("Algorithm: Error accessing local API")
                        if self.previous_alg_id == 20:
                            self.switch_high_power_profile()
                            self.previous_alg_id = None
                        if self.wallpaper_engine_toggle:
                            self.resume_wallpaper_engine()
                        time.sleep(self.interval_time)
                        continue

                    try:
                        self.current_alg_id = local_data["algorithms"][0]["algorithm_id"]
                    except IndexError:
                        logger.info("Algorithm: API online, No mining detected")
                        time.sleep(self.interval_time)
                        continue

                    if self.previous_alg_id != self.current_alg_id:
                        logger.info(f"Algorithm changed from {NiceHashAlgoIDs[self.previous_alg_id]} "
                                    f"to {NiceHashAlgoIDs[self.current_alg_id]}")
                        if self.current_alg_id == 20:
                            self.switch_low_power_profile()

                        if self.current_alg_id != 20 and self.previous_alg_id == 20:
                            self.switch_high_power_profile()

                    if self.wallpaper_engine_toggle:
                        self.pause_wallpaper_engine()
                    self.previous_alg_id = self.current_alg_id
                    logger.info(f"Algorithm: {NiceHashAlgoIDs[self.current_alg_id]}")
                else:
                    logger.info("Excavator not running")
                    if self.previous_alg_id == 20:
                        self.switch_high_power_profile()
                        self.previous_alg_id = None
                        if self.wallpaper_engine_toggle:
                            self.resume_wallpaper_engine()
            else:
                logger.info("MSI Afterburner not running.")

            time.sleep(self.interval_time)


if __name__ == "__main__":
    switcher = ProfileSwitcher(config["settings"])
    switcher.algo_monitor()
