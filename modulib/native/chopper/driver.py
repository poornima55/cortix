#!/usr/bin/env python
"""
Valmor F. de Almeida dealmeidav@ornl.gov; vfda

Cortix native Chopper module

Sat Jul 12 16:12:56 EDT 2014
"""
#*********************************************************************************
import os, sys, io, time, datetime
import random
import logging
import xml.etree.ElementTree as ElementTree
#*********************************************************************************

#*********************************************************************************
class Driver():

# Private member data
# __slots__ = [

 def __init__( self,
               inputFullPathFileName,
               ports,
               evolveTime
             ):

  assert type(ports) is list, '-> ports type %r is invalid.' % type(ports)

  self.__ports = ports

  self.__productSolids = ElementTree.ElementTree
  self.__productGas    = ElementTree.ElementTree
  self.__productFines  = ElementTree.ElementTree

  self.__endDutyTimeSolids = 0.0
  self.__endDutyTimeGas    = 0.0

  self.__inputFuelSegments = list()  # consider this the input of all fuel rods

  self.__log = logging.getLogger('launcher-chopper.chopper')
  self.__log.info('initializing an instance of Chopper')

  self.__gramDecimals = 7 # tenth microgram significant digits
  self.__mmDecimals   = 3 # micrometer significant digits
#  self.__pyplotScale  = 'log-linear' # linear, linear-linear, log, log-log, linear-log, log-linear
  self.__pyplotScale  = 'linear' # linear, linear-linear, log, log-log, linear-log, log-linear

# THIS IS A HACKING for mimicking a real chopper. The data is precomputed and
# stored into input files, these files are used to provide data to other modules.
# Will deal with this issue later.
# However this prompts the need for a better design of initialization of modules
# depending on input data files.

  fin = open(inputFullPathFileName,'r')
  inputDataFullPathFileNames = list()
  for line in fin:
   inputDataFullPathFileNames.append(line.strip())
  fin.close()

  found = False
  for port in ports:
    (portName,portType,portFile) = port
    if portName == 'solids-input':
      s = 'cp -f ' + inputDataFullPathFileNames[0] + ' ' + portFile
      os.system(s)
      self.__log.debug(s)
      found = True

  assert found, 'Input setup failed.'

  found = False
  for port in ports:
    (portName,portType,portFile) = port
    if portName == 'gas-input':
      s = 'cp -f ' + inputDataFullPathFileNames[1] + ' ' + portFile
      os.system(s)
      self.__log.debug(s)
      found = True

  assert found, 'Input setup failed.'

  found = False
  for port in ports:
    (portName,portType,portFile) = port
    if portName == 'fines-input':
      s = 'cp -f ' + inputDataFullPathFileNames[2] + ' ' + portFile
      os.system(s)
      self.__log.debug(s)
      found = True

  assert found, 'Input setup failed.'

#---------------------------------------------------------------------------------
 def CallPorts(self, evolTime=0.0):

  self.__UseData( usePortName='solids-input', evolTime=evolTime )
  self.__UseData( usePortName='gas-input', evolTime=evolTime )
  self.__UseData( usePortName='fines-input', evolTime=evolTime )

  self.__ProvideData( providePortName='solids', evolTime=evolTime )
  self.__ProvideData( providePortName='off-gas', evolTime=evolTime )
  self.__ProvideData( providePortName='fines', evolTime=evolTime )

#---------------------------------------------------------------------------------
 def Execute( self, evolTime=0.0, timeStep=1.0 ):

  s = 'Execute(): facility time [min] = ' + str(evolTime)
  self.__log.info(s)
#  gDec = self.__gramDecimals
#  s = 'Execute(): total mass [g] = ' + str(round(self.__GetMass(),gDec))
#  self.__log.info(s)
#  s = 'Execute(): # of segments  = '+str(len(self.__inputFuelSegments))
  self.__log.debug(s)

#---------------------------------------------------------------------------------
 def __UseData( self, usePortName=None, evolTime=0.0 ):

# Access the port file
  portFile = self.__GetPortFile( usePortName = usePortName )

# Get data from port files
  if usePortName == 'solids-input': self.__GetInputSolids( portFile, evolTime )
  if usePortName == 'gas-input': self.__GetInputGas( portFile, evolTime )
  if usePortName == 'fines-input': self.__GetInputFines( portFile, evolTime )

#---------------------------------------------------------------------------------
 def __ProvideData( self, providePortName=None, evolTime=0.0 ):

# Access the port file
  portFile = self.__GetPortFile( providePortName = providePortName )

# Send data to port files
  if portFile is not None:
    if providePortName == 'solids': self.__ProvideSolids( portFile, evolTime )
    if providePortName == 'off-gas': self.__ProvideOffGas( portFile, evolTime )
    if providePortName == 'fines': self.__ProvideFines( portFile, evolTime )

#---------------------------------------------------------------------------------
 def __GetPortFile( self, usePortName=None, providePortName=None ):

  portFile = None

  #..........
  # Use ports
  #..........
  if usePortName is not None:

    assert providePortName is None

    for port in self.__ports:
      (portName,portType,thisPortFile) = port
      if portName == usePortName and portType == 'use': portFile = thisPortFile

    assert portFile is not None

    maxNTrials = 50
    nTrials    = 0
    while not os.path.isfile(portFile) and nTrials < maxNTrials:
      nTrials += 1
      time.sleep(1)

    if nTrials >= 10:
      s = '__GetPortFile(): waited ' + str(nTrials) + ' trials for port: ' + portFile
      self.__log.warn(s)

    assert os.path.isfile(portFile) is True, 'portFile %r not available; stop.' % portFile
  #..............
  # Provide ports
  #..............
  if providePortName is not None:

    assert usePortName is None

    for port in self.__ports:
      (portName,portType,thisPortFile) = port
      if portName == providePortName and portType == 'provide': portFile = thisPortFile

  return portFile

#---------------------------------------------------------------------------------
# This uses a use portFile which is guaranteed at this point
 def __GetInputSolidsTEST( self, portFile, evolTime ):

  tree = ElementTree.parse(portFile)

  rootNode = tree.getroot()

  durationNode = rootNode.find('Duration')

  timeStep = float(durationNode.get('timeStep'))
  s = '__GetSolids(): timeStep='+str(timeStep)
  self.__log.debug(s)

  streamNode = rootNode.find('Stream')
  s = '__GetSolids(): streamNode='+streamNode.get('name')
  self.__log.debug(s)

  timeNodes = streamNode.findall('Time')
  s = '__GetSolids(): # time nodes ='+str(len(timeNodes))
  self.__log.debug(s)

#.................................................................................
  for timeNode in timeNodes:

   totalMass = 0.0

   U    = 0.0
   Pu   = 0.0
   Cs   = 0.0
   Sr   = 0.0
   I    = 0.0
   Kr   = 0.0
   Xe   = 0.0
   a3H  = 0.0
   Ru   = 0.0
   O    = 0.0
   N    = 0.0
   FP   = 0.0

   timeIndex = int(timeNode.get('index'))

#   s = '__GetSolids(): timeIndex='+str(timeIndex)
#   self.__log.debug(s)

   timeStamp = timeStep*timeIndex          

#   s = '__GetSolids(): timeStamp='+str(timeStamp)
#   self.__log.debug(s)

   if timeStamp == evolTime: 

#     s = '__GetSolids(): timeStamp='+str(timeStamp)+';'+' evolTime='+str(evolTime)
#     self.__log.debug(s)

     n = timeNode.find('Segment_Length')
 
     if not ElementTree.iselement(n): continue # to the next timeNode
 
     segmentLength = float(n.get('length'))
     segmentLengthUnit = n.get('unit')
     if   segmentLengthUnit == 'm':  segmentLength *= 1000.0
     elif segmentLengthUnit == 'cm': segmentLength *= 10.0
     elif segmentLengthUnit == 'mm': segmentLength *= 1.0
     else:                            assert True, 'invalid unit.'
        
     n = timeNode.find('Segment_Outside_Diameter')
     oD = float(n.get('outside_diameter'))
     oDUnit = n.get('unit')
     if   oDUnit == 'm':  oD *= 1000.0
     elif oDUnit == 'cm': oD *= 10.0
     elif oDUnit == 'mm': oD *= 1.0
     else:                assert True, 'invalid unit.'

     n = timeNode.find('Segment_Inside_Diameter')
     iD = float(n.get('inside_diameter'))
     iDUnit = n.get('unit')
     if   iDUnit == 'm':  iD *= 1000.0
     elif iDUnit == 'cm': iD *= 10.0
     elif iDUnit == 'mm': iD *= 1.0
     else:                assert True, 'invalid unit.'

     n = timeNode.find('Segments_Output_This_Timestep')
     nSegments = float(n.get('segments_output'))

     elements = timeNode.findall('Element')
     for element in elements:
       isotopes = element.findall('Isotope')
       for isotope in isotopes:
        for child in isotope:
           if child.tag == 'Mass': 
              mass = float(child.text.strip())
              totalMass += mass
              if element.get('key') == 'U' :  U  += mass; 
              if element.get('key') == 'Pu':  Pu += mass; 
              if element.get('key') == 'Cs':  Cs += mass; 
              if element.get('key') == 'Sr':  Sr += mass; 
              if element.get('key') == 'I' :  I  += mass; 
              if element.get('key') == 'Kr':  Kr += mass; 
              if element.get('key') == 'Kr':  Xe += mass; 
              if element.get('key') == 'H' : a3H += mass; 
              if element.get('key') == 'Ru':  Ru += mass; 
              if element.get('key') == 'O' :  O  += mass; 
              if element.get('key') == 'N' :  N  += mass; 

     FP = totalMass - (U + Pu + I + Kr + Xe + a3H)

     for seg in range(1,int(nSegments)+1):
      segMass   = totalMass / int(nSegments)
      segLength = segmentLength
      segID     = iD
      U         = U  / int(nSegments)
      Pu        = Pu / int(nSegments)
      I         = I  / int(nSegments)
      Kr        = Kr / int(nSegments)
      Xe        = Xe / int(nSegments)
      a3H       = a3H/ int(nSegments)
      FP        = FP / int(nSegments)
      segment   = ( timeStamp, segMass, segLength, segID, 
                    U, Pu, I, Kr, Xe, a3H, FP )

      self.__inputFuelSegments.append( segment )
  
     break

  return

#---------------------------------------------------------------------------------
# This uses a use portFile which is guaranteed at this point
 def __GetInputSolids( self, portFile, evolTime ):

   self.__productSolids     = ElementTree.parse(portFile)
   self.__endDutyTimeSolids = self.__GetEndDutyTime( self.__productSolids )

   return

#---------------------------------------------------------------------------------
# This uses a use portFile which is guaranteed at this point
 def __GetInputGas( self, portFile, evolTime ):

   self.__productGas     = ElementTree.parse(portFile)
   self.__endDutyTimeGas = self.__GetEndDutyTime( self.__productGas )

   return

#---------------------------------------------------------------------------------
# This uses a use portFile which is guaranteed at this point
 def __GetInputFines( self, portFile, evolTime ):

   self.__productFines = ElementTree.parse(portFile)

   return

#---------------------------------------------------------------------------------
# Provide the entire history data 
 def __ProvideSolids( self, portFile, evolTime ):

   if evolTime == 0.0:
      self.__productSolids.write( portFile, xml_declaration=True, encoding="unicode", 
                                  method="xml" )
   return

#---------------------------------------------------------------------------------
# Provide the entire history data 
 def __ProvideFines( self, portFile, evolTime ):
   return

#---------------------------------------------------------------------------------
 def __ProvideOffGas( self, portFile, evolTime ):

  gDec = self.__gramDecimals

  if evolTime > self.__endDutyTimeGas: return

  # if the first time step, write the header of a time-sequence data file
  if evolTime == 0.0:

    assert os.path.isfile(portFile) is False, 'portFile %r exists; stop.' % portFile

    tree = ElementTree.ElementTree()
    rootNode = tree.getroot()

    a = ElementTree.Element('time-sequence')
    a.set('name','chopper-offgas')

    b = ElementTree.SubElement(a,'comment')
    today = datetime.datetime.today()
    b.set('author','cortix.modules.native.chopper')
    b.set('version','0.1')

    b = ElementTree.SubElement(a,'comment')
    today = datetime.datetime.today()
    b.set('today',str(today))

    b = ElementTree.SubElement(a,'time')
    b.set('unit','minute')
    cutOff = self.__endDutyTimeGas
    b.set('cut-off',str(cutOff))

    # first variable
    b = ElementTree.SubElement(a,'var')
    b.set('name','Xe Off-Gas')
    b.set('unit','gram/min')
    b.set('legend','Chopper-offgas')
    b.set('scale',self.__pyplotScale)

    # values for all variables
    b = ElementTree.SubElement(a,'timeStamp')
    b.set('value',str(evolTime))
    mass = round(self.__GetXeMassGas(evolTime),gDec)
    b.text = str(mass)

    tree = ElementTree.ElementTree(a)

    tree.write( portFile, xml_declaration=True, encoding="unicode", method="xml" )

  # if not the first time step then parse the existing history file and append
  else:

    tree = ElementTree.parse( portFile )
    rootNode = tree.getroot()
    a = ElementTree.Element('timeStamp')
    a.set('value',str(evolTime))
    mass = round(self.__GetXeMassGas(evolTime),gDec)
    factor = 1.0 + (2.0*random.random()-1.0) * 0.15/2.0
    mass *= factor # add a total of 15% variability (+-7.5%)
    a.text = str(mass)

    rootNode.append(a)

    tree.write( portFile, xml_declaration=True, encoding="unicode", method="xml" )

  return 

#---------------------------------------------------------------------------------
 def __GetXeMassGas( self, evolTime ):

  Xe = 0.0

  tree = self.__productGas

  rootNode = tree.getroot()
  durationNode = rootNode.find('Duration')

  timeStep = float(durationNode.get('timeStep'))
  s = '__GetXeMassGas(): timeStep='+str(timeStep)
  self.__log.debug(s)

  streamNode = rootNode.find('Stream')
  s = '__GetXeMassGas(): streamNode='+streamNode.get('name')
  self.__log.debug(s)
 
  timeNodes = streamNode.findall('Time')
  s = '__GetXeMassGas(): # time nodes ='+str(len(timeNodes))
  self.__log.debug(s)

#.................................................................................
  for timeNode in timeNodes:

   timeIndex = int(timeNode.get('index'))

   timeStamp = timeStep*timeIndex          

   if timeStamp == evolTime: 

     Xe = 0.0

     elements = timeNode.findall('Element')
     for element in elements:
       isotopes = element.findall('Isotope')
       for isotope in isotopes:
        for child in isotope:
           if child.tag == 'Mass': 
              mass = float(child.text.strip())
              if element.get('key') == 'Xe':  Xe += mass; 

     break

  return Xe

#---------------------------------------------------------------------------------
 def __GetEndDutyTime( self, tree ):

  endDutyTime = 0.0

  rootNode = tree.getroot()
  durationNode = rootNode.find('Duration')

  timeStep = float(durationNode.get('timeStep'))
  s = '__GetEndDutyTime(): timeStep='+str(timeStep)
  self.__log.debug(s)

  streamNode = rootNode.find('Stream')
  s = '__GetEndDutyTime(): streamNode='+streamNode.get('name')
  self.__log.debug(s)
 
  timeNodes = streamNode.findall('Time')
  s = '__GetEndDutyTime(): # time nodes ='+str(len(timeNodes))
  self.__log.debug(s)

#.................................................................................
  for timeNode in timeNodes:
   timeIndex = int(timeNode.get('index'))
   timeStamp = timeStep*timeIndex          
   endDutyTime = max(endDutyTime, timeStamp)

  return endDutyTime

#*********************************************************************************
# Usage: -> python fuelaccumulation.py
if __name__ == "__main__":
 print('Unit testing for Chopper')