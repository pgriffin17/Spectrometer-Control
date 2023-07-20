# -*- coding: utf-8 -*-
"""
Created on Mon May 22, 2023

@author: Bill Peterson
"""

from spectrometerClass import *

try:
    spec = Spectrometer()
except:
    raise
else:
    print("Connected.")

while True:
    cmd = input('Enter command: ')
    spec.giveCommand(cmd)
