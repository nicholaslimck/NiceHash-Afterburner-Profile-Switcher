import time
import socket
import subprocess
import APIRequests
import psutil

import ctypes
import sys

from configparser import ConfigParser
from loguru import logger
from NiceHashAlgoID import Dict as NiceHashAlgoIDs

config = ConfigParser()
config.read("config.ini")
logger.add('logs/profileSwitcher.log')


class ProfileSwitcher:
    def __init__(self, settings):
        self.version = "0.3"
        self.excavator_name = "excavator"
        self.interval_time = int(settings['interval_time'])
        self.msi_application_location = settings['msi_application_location']
        self.excavator_address = (settings['excavator_ip'], int(settings['excavator_port']))
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

    def check_excavator_running(self):
        """
        Checks if excavator is running.
        Returns:
            bool: True if excavator is running. False otherwise.
        """
        for proc in psutil.process_iter():
            try:
                # Check if process name contains the given name string.
                if self.excavator_name.lower() in proc.name().lower():
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        return False

    def switch_low_power_profile(self):
        """
        Switch MSI Afterburner to configured Low Power Profile
        """
        logger.info("Changing MSI Afterburner to Low Power Mode")
        if self.elevated_privileges:
            subprocess.Popen([self.msi_application_location, f"-profile{self.low_power_profile['profile_num']}"],
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
            subprocess.Popen([self.msi_application_location, f"-profile{self.high_power_profile['profile_num']}"],
                             shell=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        elif self.scheduled_tasks_present:
            subprocess.Popen([r"C:\Windows\System32\schtasks.exe", "/RUN", "/TN",
                              self.high_power_profile['profile_name']],
                             shell=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    def algo_monitor(self):
        """
        Main algorithm monitor loop.
        """
        logger.info(f"Starting Algorithm Monitor v{self.version}")

        if self.elevated_privileges:
            logger.info("Elevated privileges detected")
        elif self.scheduled_tasks_present:
            logger.info("Elevated privileges not detected but scheduled tasks present")
        # else:
        #     logger.info("No elevated privileges or scheduled tasks detected, exiting...")
        #     sys.exit(0)

        # Main Loop
        while True:
            # localAPI
            if self.check_excavator_running():
                try:
                    local_data = APIRequests.dict_from_tcp(self.excavator_address,
                                                           {"id": 1, "method": "algorithm.list", "params": []})
                except socket.error as error:
                    logger.error(error)
                    logger.info("Algorithm: Error accessing local API")
                    if self.previous_alg_id == 20:
                        self.switch_high_power_profile()
                        self.previous_alg_id = None
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
                self.previous_alg_id = self.current_alg_id
                logger.info(f"Algorithm: {NiceHashAlgoIDs[self.current_alg_id]}")
            else:
                logger.info("Excavator not running.")
                if self.previous_alg_id == 20:
                    self.switch_high_power_profile()
                    self.previous_alg_id = None

            time.sleep(self.interval_time)


if __name__ == "__main__":
    switcher = ProfileSwitcher(config["settings"])
    switcher.algo_monitor()
