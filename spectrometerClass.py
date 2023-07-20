# Spectrometer object used to control Newport MS260i 
# spectrometer with python

import usb.core
import usb.util
import time


class Spectrometer:
    def __init__(self):
        '''
        Initialize the spectrometer object, connect to the spectrometer,
        and set the configuration
        
        Raises
        ------
        ValueError
            If the spectrometer is not found
            
        Returns
        -------
        None
        '''
        self.dev = usb.core.find(idVendor = 0x1180, idProduct = 0x0012)
        #self.dev.reset()

        if self.dev is None:
            raise ValueError('Device not found.')

        self.dev.set_configuration()

        cfg = self.dev.get_active_configuration()
        intf = cfg[(0,0)]

        ep = usb.util.find_descriptor(
            intf,
            custom_match = \
            lambda e: \
                usb.util.endpoint_direction(e.bEndpointAddress) == \
                usb.util.ENDPOINT_OUT)

        assert ep is not None
        
        self.units = ['nm', 'um', 'wn']
        self.auto = False
        self.unit = self.getUnits()

    def giveCommand(self, string):
        '''
        Send a command to the spectrometer, commands are listed in the
        spectrometer manual.

        Parameters
        ----------
        string : str
            Command to send to the spectrometer

        Returns
        -------
        str
            Response from the spectrometer
        '''
        #print(string)
        command = string.split()[0]
        subtract = False
        if command == 'gowave':
            value = float(string.split()[1])
            string = command + ' ' + str(value + 73)
            #print(string)
        elif command == 'wave?':
            subtract = True
        self.dev.write(1, encode(string), 1000)
        if string[-1] == '?':
            r = self.read()
            if subtract:
                return str(float(r) - self.convert(73,'nm', self.unit))
            return r
        else:
            #
            sb = self.getStatusByte()
            while not ('00' == sb or '32' in sb):
                sb = self.getStatusByte()
                #self.updateEntry(self.statusEntry, "Moving...")
                #print('moving')
                #self.update_idletasks()
            #

    def read(self):
        '''
        Internal function to read the response from the spectrometer

        Returns
        -------
        str
            Response from the spectrometer
        '''
        #self.giveCommand(command)
        time.sleep(.2)
        r = self.dev.read(0x81, 64, 100)
        sr = ''.join([chr(x) for x in r])
        time.sleep(.2)
        #print(sr)
        return sr.split('\r')[0] #[s.strip() for s in sr.split('\r')][0]

    def setGrating(self, grat):
        '''
        Takes grat, an integer between 1 and 3, and tells spectrometer
        to make that the active grating.
        
        Parameters
        ----------
        grat : int
            Grating to set the spectrometer to
            
        Returns
        -------
        int
            1 when completed
        '''
        if self.validGratingInput(grat) and int(grat) != int(self.getGrating()[0]):
            self.giveCommand('grat ' + str(grat))
            #time.sleep(5)
        return 1

    def getGrating(self):
        '''
        Get the current grating's number, lines per mm, and blaze wavelength
        in a list of strings.

        Returns
        -------
        list
            [grating, lines per mm, blaze wavelength]
        '''
        try:
            return self.giveCommand('grat?').split(',')
        except:
            return [0,0,0]

    def getUnits(self):
        '''
        Get the current units that the spectrometer is using
        (nm, um, or wv = wavenumbers)
        
        Returns
        -------
        str
            Current units (or 0 if not nm, um, or wn)
        '''
        u = self.giveCommand('units?')
        if u in self.units:
            return u
        #print(u)
        return 0

    def setUnits(self, unit):
        '''
        Set the spectrometer's current units to use the input units
        as long as the input is in [nm, um, wn]
        
        Parameters
        ----------
        unit : str
            Units to set the spectrometer to
            
        Returns
        -------
        int
            1 if successful, 0 if not a valid unit
        '''
        unit = unit.lower()
        if unit in self.units:
            self.giveCommand('units ' + unit)
            self.unit = unit
            return 1
        return 0

    # Returns true if input can be turned into an int between 1 and 3
    def validGratingInput(self, grat):
        '''
        Check if the input can be turned into an integer between 1 and 3
        
        Parameters
        ----------
        grat : int or str
            Input to check
        
        Returns
        -------
        bool
            True if input is a valid grating, False if not'''
        try:
            grat = int(grat)
            return 0 < grat < 4
        except:
            return False

    def openShutter(self):
        '''
        Open the shutter on the spectrometer (shutter does not exist on
        our spectrometer, so this function does nothing)
        '''
        self.giveCommand('shutter o')

    def closeShutter(self):
        '''
        Close the shutter on the spectrometer (shutter does not exist on
        our spectrometer, so this function does nothing)'''
        self.giveCommand('shutter c')

    def getShutter(self):
        '''
        Get the status of the shutter on the spectrometer (shutter does not
        exist on our spectrometer, so this function does nothing)
        '''
        return self.giveCommand('shutter?')

    def setAuto(self, b):
        '''
        Set the spectrometer to automatically change gratings based on
        the wavelength being set
        
        Parameters
        ----------
        b : bool
            True to turn on auto, False to turn off auto
            
        Returns
        -------
        int
            1 if successful, 0 if not a bool'''
        if type(b) == bool:
            self.auto = b
            return 1
        else:
            return 0

    def setWavelength(self, wavelength, units = 'nm'):
        '''
        Set the spectrometer to the input wavelength and units
        
        Parameters
        ----------
        wavelength : float
            Wavelength to set the spectrometer to
        units : str, optional
            Units of the wavelength, by default 'nm'
            
        Returns
        -------
        int
            1 if successful, 0 if not a valid unit
        '''
        if self.auto:
            nw = self.convert(wavelength, units, 'nm')
            if nw < 430:
                self.setGrating(1)
            elif nw > 625:
                self.setGrating(3)
            else:
                self.setGrating(2)
            #time.sleep(10)
        curUnits = self.getUnits()
        if units.lower() != curUnits:
            #print('problem here')
            wavelength = self.convert(wavelength, units, curUnits)
        #print('here')
        self.giveCommand('gowave ' + str(wavelength))
        #time.sleep(1)

    def convert(self, w, u, c):
        '''
        Convert the input wavelength (w) from the input units (u) to the 
        current units (c) of the spectrometer
        
        Parameters
        ----------
        w : float
            Wavelength to convert
        u : str
            Units of the wavelength
        c : str
            Units to convert the wavelength to
        
        Returns
        -------
        float
            Converted wavelength
        '''
        if u == 'um':
            w *= 10**3  # convert um to nm
        elif u == 'wn':
            w = 10**7 / w  # convert wn to nm
        if c == 'nm':
            return w  # if we want nm, return w
        elif c == 'um':
            return w / 10**3  # convert nm to um, return
        else:
            return 10**7 / w  # convert nm to wn, return

    def getWavelength(self):
        '''
        Get the current wavelength of the spectrometer
        
        Returns
        -------
        float
            Current wavelength, or 0 if command fails'''
        try:
            return float(self.giveCommand('wave?'))
        except:
            return 0

    # Returns the # of lines per mm of the grating.  Currently,
    # all gratings have 1200 lpm
    def getGratingLines(self, grat):
        '''
        Get the number of lines per mm of the input grating
        
        Parameters
        ----------
        grat : int
            Grating to get the lines per mm of
            
        Returns
        -------
        int
            Number of lines per mm of the input grating, or 0 if not a valid
            grating
        '''
        if self.validGratingInput(grat):
            grat = str(int(grat))
            return self.giveCommand('grat' + grat + 'lines?')
        return 0

    def getStatusByte(self):
        '''
        Get the status byte of the spectrometer
        
        Returns
        -------
        str
            Status byte of the spectrometer
        '''
        return self.giveCommand('stb?')
            
    def getErrorByte(self):
        '''
        Get the error byte of the spectrometer
        
        Returns
        -------
        str
            Error byte of the spectrometer
        '''
        return self.giveCommand('error?')

    # Returns ['1', '1200', '360', '2', '1200', '500', '3', '1200', '750']
    # don't need to run unless gratings changed
    def getGratingsInfo(self):
        '''
        Get the information of all 3 gratings on the spectrometer
        
        Returns
        -------
        list
            List of strings containing the grating number, lines per mm,
            and blaze wavelength of each grating
        '''
        gratings = []
        for i in range(1,4):
            self.setGrating(i)
            input('enter when done moving')
            gratings += self.getGrating()
        return gratings

    def setAuto(self,setTo):
        '''
        Set the spectrometer to automatically change gratings based on
        the wavelength being set
        
        Parameters
        ----------
        setTo : bool
            True to turn on auto, False to turn off auto
            
        Returns
        -------
        None
        '''
        if type(setTo) != bool:
            return
        self.auto = setTo

    def finish(self):
        '''
        Close the connection to the spectrometer
        '''
        usb.util.dispose_resources(self.dev)
    def reset(self):
        '''
        Reset the connection to the spectrometer
        '''
        self.dev.reset()



def encode(string):
    return (string + '\n').encode('ascii', 'replace')
            
def restart():
    sp = Spectrometer()
    sp.finish()
    sp.reset()




    
