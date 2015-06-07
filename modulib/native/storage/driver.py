#!/usr/bin/env python
"""
Valmor F. de Almeida dealmeidav@ornl.gov; vfda

Cortix native Storage module

Tue Jun 24 01:03:45 EDT 2014
"""
#*********************************************************************************
import os, sys, io, time, datetime
import math, random
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
               evolveTime=0.0
             ):

  # Sanity test
  assert type(ports) is list, '-> ports type %r is invalid.' % type(ports)
  assert type(evolveTime) is float, '-> time type %r is invalid.' % type(evolveTime)

  # Logging
  self.__log = logging.getLogger('launcher-storage.storage')
  self.__log.info('initializing an instance of Storage')

  # Member data
  self.__ports = ports

  self.__evolveTime = evolveTime

  self.__fuelSegments = list()

  self.__withdrawMass = 0.0
 
  self.__historyXeMassOffGas = dict()
  self.__historyXeMassOffGas[0.0] = 0.0

  self.__historyKrMassOffGas = dict()
  self.__historyKrMassOffGas[0.0] = 0.0

  self.__historyI2MassOffGas = dict()
  self.__historyI2MassOffGas[0.0] = 0.0

  self.__gramDecimals = 7 # tenth microgram significant digits
  self.__mmDecimals   = 3 # micrometer significant digits
  self.__ccDecimals   = 3 # microcc significant digits
  self.__pyplotScale = 'linear' # linear, linear-linear, log, log-log, linear-log, log-linear

#---------------------------------------------------------------------------------
 def CallPorts(self, facilityTime=0.0):

  self.__UseData( usePortName='solids', atTime=facilityTime )
 
  self.__UseData( usePortName='withdrawal-request', atTime=facilityTime  )

  self.__ProvideData( providePortName='fuel-segments', atTime=facilityTime )

  self.__ProvideData( providePortName='off-gas', atTime=facilityTime )

  # make this always last
  self.__ProvideData( providePortName='state', atTime=facilityTime )

#---------------------------------------------------------------------------------
 def Execute( self, facilityTime=0.0, timeStep=0.0 ):

  s = 'Execute(): facility time [min] = ' + str(facilityTime)
  self.__log.info(s)
  gDec = self.__gramDecimals
  s = 'Execute(): total mass [g] = ' + str(round(self.__GetMass(),gDec))
  self.__log.info(s)
  s = 'Execute(): # of segments  = '+str(len(self.__fuelSegments))
  self.__log.debug(s)

  self.__Store( facilityTime, timeStep )

#---------------------------------------------------------------------------------
 def __UseData( self, usePortName=None, atTime=0.0 ):

# Access the port file
  portFile = self.__GetPortFile( usePortName=usePortName )

# Get data from port files
  if usePortName == 'solids': self.__GetSolids( portFile, atTime )

  if usePortName == 'withdrawal-request': self.__GetWithdrawalRequest( portFile, atTime )

#---------------------------------------------------------------------------------
 def __ProvideData( self, providePortName=None, atTime=0.0 ):

# Access the port file
  portFile = self.__GetPortFile( providePortName=providePortName )

# Send data to port files
  if providePortName == 'fuel-segments' and portFile is not None: 
     self.__ProvideFuelSegmentsOnDemand( portFile, atTime )

  if providePortName == 'off-gas' and portFile is not None:
     self.__ProvideOffGas( portFile, atTime )

  if providePortName == 'state' and portFile is not None:
     self.__ProvideState( portFile, atTime )

#---------------------------------------------------------------------------------
 def __GetPortFile( self, usePortName=None, providePortName=None ):

  portFile = None

  #..........
  # Use ports
  #..........
  if usePortName is not None:

    assert providePortName is None

    for port in self.__ports:
     if port[0] == usePortName and port[1] == 'use': portFile = port[2]

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
     if port[0] == providePortName and port[1] == 'provide': portFile = port[2]

  return portFile

#---------------------------------------------------------------------------------
# This uses a use portFile which is guaranteed at this point
 def __GetSolids( self, portFile, facilityTime ):

  found = False

  while found is False:

    try:
      tree = ElementTree.parse( portFile )
    except ElementTree.ParseError as error:
      s = '__GetSolids(): '+portFile+' unavailable. Error code: '+str(error.code)+' File position: '+str(error.position)+'. Retrying...'
      self.__log.debug(s)
      continue

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

     timeIndex = int(timeNode.get('index'))

#   s = '__GetSolids(): timeIndex='+str(timeIndex)
#   self.__log.debug(s)

     timeStamp = timeStep*timeIndex          

#   s = '__GetSolids(): timeStamp='+str(timeStamp)
#   self.__log.debug(s)
  
     if timeStamp == facilityTime: 

       #...........
       found = True
       #...........

#     s = '__GetSolids(): timeStamp='+str(timeStamp)+';'+' facilityTime='+str(facilityTime)
#     self.__log.debug(s)

       n = timeNode.find('Segment_Length')
 
       if not ElementTree.iselement(n): continue # to the next timeNode
 
       # NB: volume variability is the linear variability to the CUBE power

       segmentLength = float(n.get('length'))
       factor = 1.0 + (2.0*random.random()-1.0) * 0.025/2.0
       segmentLength *= factor # add a total of 2.5% variability (+-1.25%)
       segmentLengthUnit = n.get('unit')
       if   segmentLengthUnit == 'm':  segmentLength *= 1000.0
       elif segmentLengthUnit == 'cm': segmentLength *= 10.0
       elif segmentLengthUnit == 'mm': segmentLength *= 1.0
       else:                            assert True, 'invalid unit.'
        
       n = timeNode.find('Segment_Outside_Diameter')
       oD = float(n.get('outside_diameter'))
       factor = 1.0 + (2.0*random.random()-1.0) * 0.025/2.0
       oD *= factor # add a total of 2.5% variability (+-1.25%)
       oDUnit = n.get('unit')
       if   oDUnit == 'm':  oD *= 1000.0
       elif oDUnit == 'cm': oD *= 10.0
       elif oDUnit == 'mm': oD *= 1.0
       else:                assert True, 'invalid unit.'

       n = timeNode.find('Segment_Inside_Diameter')
       iD = float(n.get('inside_diameter'))
       factor = 1.0 + (2.0*random.random()-1.0) * 0.025/2.0
       iD *= factor # add a total of 2.5% variability (+-1.25%)
       iDUnit = n.get('unit')
       if   iDUnit == 'm':  iD *= 1000.0
       elif iDUnit == 'cm': iD *= 10.0
       elif iDUnit == 'mm': iD *= 1.0
       else:                assert True, 'invalid unit.'

       n = timeNode.find('Segments_Output_This_Timestep')
       nSegments = float(n.get('segments_output'))

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
       C    = 0.0

       elements = timeNode.findall('Element')
       for element in elements:
         isotopes = element.findall('Isotope')
         for isotope in isotopes:
          for child in isotope:
             if child.tag == 'Mass': 
                mass = float(child.text.strip())
                factor = 1.0 + (2.0*random.random()-1.0) * 0.15/2.0
                mass *= factor # add a total of 15% variability (+-7.5%)
                totalMass += mass
                if element.get('key') == 'U' :  U  += mass; 
                if element.get('key') == 'Pu':  Pu += mass; 
                if element.get('key') == 'Cs':  Cs += mass; 
                if element.get('key') == 'Sr':  Sr += mass; 
                if element.get('key') == 'I' :  I  += mass; 
                if element.get('key') == 'Kr':  Kr += mass; 
                if element.get('key') == 'Xe':  Xe += mass; 
                if element.get('key') == 'H' : a3H += mass; 
                if element.get('key') == 'Ru':  Ru += mass; 
                if element.get('key') == 'O' :  O  += mass; 
                if element.get('key') == 'N' :  N  += mass; 
                if element.get('key') == 'C' :  C  += mass; 

#  print('mass     [g]= ', mass)
#  print('#segments   = ', nSegments)
#  print('length      = ', segmentLength)
#  print('OD          = ', oD)
#  print('ID          = ', iD)

       # end of: for element in elements:

       FP = totalMass - (U + Pu + I + Kr + Xe + a3H + Ru + C)

#     totalNSegments += nSegments

#  print('mass U      = ', U)
#  print('mass Pu     = ', Pu)
#  print('mass Cs     = ', Cs)
#  print('mass I      = ', I)
#  print('mass O      = ', O)
#  print('mass N      = ', N)
#  print('mass FP     = ', FP)

       gDec  = self.__gramDecimals 
       mmDec = self.__mmDecimals 

       totalMass     = round(totalMass,gDec)
       segmentLength = round(segmentLength,mmDec)
       iD            = round(iD,mmDec)

       assert abs( totalMass - (U+Pu+I+Kr+Xe+a3H+Ru+C+FP) ) < 1.0e-2

       segMass   = totalMass / int(nSegments)
       segLength = segmentLength
       segID     = iD
       U         /=  int(nSegments)
       Pu        /=  int(nSegments)
       I         /=  int(nSegments)
       Kr        /=  int(nSegments)
       Xe        /=  int(nSegments)
       a3H       /=  int(nSegments)
       Ru        /=  int(nSegments)
       C         /=  int(nSegments)
       FP        /=  int(nSegments)

       U   = round(U  ,gDec)
       Pu  = round(Pu ,gDec)
       I   = round(I  ,gDec)
       Kr  = round(Kr ,gDec)
       Xe  = round(Xe ,gDec)
       a3H = round(a3H,gDec)
       Ru  = round(Ru ,gDec)
       C   = round(C  ,gDec)
       FP  = round(FP ,gDec)

       assert abs( segMass - (U+Pu+I+Kr+Xe+a3H+Ru+C+FP) ) < 1.0e-2

       for seg in range(int(nSegments)):

         segment = ( timeStamp, segMass, segLength, segID, 
                     U, Pu, I, Kr, Xe, a3H, Ru, C, FP )

         self.__fuelSegments.append( segment )
#         print( '# segments = ', len(self.__fuelSegments) )

       # end of: for seg in range(1,int(nSegments)+1):
  
#  print('totalMass     [g]= ', totalMass)
#  print('total # segments = ', totalNSegments)
#  print('total # pieces   = ', len(self.__fuelSegments))
#  print('total U       [g]= ', totalU)
#  print('total Pu      [g]= ', totalPu)
#  print('total Cs      [g]= ', totalCs)
#  print('total I       [g]= ', totalI)
#  print('total O       [g]= ', totalO)
#  print('total N       [g]= ', totalN)
#  print('total FP      [g]= ', totalFP)
  
#  print(self.__fuelSegments)
#  for s in self.__fuelSegments:
#   print(s[0],s[1],s[2])

       break # out of the timeNode loop

     # end of: if timeStamp == facilityTime: 

    # end of: for timeNode in timeNodes:

    if found is False: time.sleep(1) 

  # end of: while found is False:

#  print('facility time ',facilityTime)
#  print('fuel segments ',self.__fuelSegments)
  assert self.__GetMassCheck() is True, 'mass imbalance at facility time %r; stop.' % facilityTime 

  return

#---------------------------------------------------------------------------------
# This uses a use portFile which is guaranteed to exist at this point
 def __GetWithdrawalRequest( self, portFile, facilityTime ):

  found = False

  while found is False:

    s = '__GetWithdrawalRequest(): checking for withdrawal message at '+str(facilityTime)
    self.__log.debug(s)

    try:
      tree = ElementTree.parse( portFile )
    except ElementTree.ParseError as error:
      s = '__GetWithdrawalRequest(): '+portFile+' unavailable. Error code: '+str(error.code)+' File position: '+str(error.position)+'. Retrying...'
      self.__log.debug(s)
      continue

    rootNode = tree.getroot()
    assert rootNode.tag == 'time-sequence', 'invalid cortex file format; stop.' 

    node = rootNode.find('time')
    timeUnit = node.get('unit').strip()
    assert timeUnit == "minute"

    # vfda to do: check for single var element
    node = rootNode.find('var')
    assert node.get('name').strip() == 'Fuel Request', 'invalid variable.'
    assert node.get('unit').strip() == 'gram', 'invalid mass unit'

    nodes = rootNode.findall('timeStamp')

    for n in nodes:

      timeStamp = float(n.get('value').strip())
 
      # get data at timeStamp facilityTime
      if timeStamp == facilityTime:

         found = True

         mass = 0.0
         mass = float(n.text.strip())
         self.__withdrawMass = mass

         s = '__GetWithdrawalRequest(): received withdrawal message at '+str(facilityTime)+' [min]; mass [g] = '+str(round(mass,3))
         self.__log.debug(s)

    # end for n in nodes:

    if found is False: time.sleep(1) 

  # end of while found is False:

  return 

#---------------------------------------------------------------------------------
 def __GetMass(self, timeStamp=None):
 
  mass = 0.0

  if timeStamp is None:
     for fuelSeg in self.__fuelSegments:
      mass += fuelSeg[1]

  else:
     for fuelSeg in self.__fuelSegments:
      if fuelSeg[0] <= timeStamp: mass += fuelSeg[1]

  return mass

#---------------------------------------------------------------------------------
 def __GetUMass(self, timeStamp=None):
 
  mass = 0.0

  if timeStamp is None:
     for fuelSeg in self.__fuelSegments:
      mass += fuelSeg[4]

  else:
     for fuelSeg in self.__fuelSegments:
      if fuelSeg[0] <= timeStamp: mass += fuelSeg[4]

  return mass

#---------------------------------------------------------------------------------
 def __GetPuMass(self, timeStamp=None):
 
  mass = 0.0

  if timeStamp is None:
     for fuelSeg in self.__fuelSegments:
      mass += fuelSeg[5]

  else:
     for fuelSeg in self.__fuelSegments:
      if fuelSeg[0] <= timeStamp: mass += fuelSeg[5]

  return mass

#---------------------------------------------------------------------------------
 def __GetXeMass(self, timeStamp=None):
 
  mass = 0.0

  if timeStamp is None:
     for fuelSeg in self.__fuelSegments:
      mass += fuelSeg[8]

  else:
     for fuelSeg in self.__fuelSegments:
      if fuelSeg[0] <= timeStamp: mass += fuelSeg[8]

  return mass


#---------------------------------------------------------------------------------
 def __GetFPMass(self, timeStamp=None):
 
  mass = 0.0

  if timeStamp is None:
     for fuelSeg in self.__fuelSegments:
      mass += fuelSeg[10]

  else:
     for fuelSeg in self.__fuelSegments:
      if fuelSeg[0] <= timeStamp: mass += fuelSeg[10]

  return mass

#---------------------------------------------------------------------------------
# Provide the entire history data 
 def __ProvideFuelSegmentsOnDemand( self, portFile, atTime ):

  gDec  = self.__gramDecimals
  mmDec = self.__mmDecimals

  # fuel segments at time=atTime have different time stamps when they were first cut
  vars1 = [('cutTimeStamp','minute'),
           ('mass','gram'),
           ('length','mm'),
           ('innerDiameter','mm'),
           ('volume','cc'),
           ('massDensity','g/cc'),
          ]

  vars2 = [('U','gram'),
           ('Pu','gram'),
           ('I','gram'),
           ('Kr','gram'),
           ('Xe','gram'),
           ('3H','gram'),
           ('Ru','gram'),
           ('C','gram'),
           ('FP','gram')
          ]

  withdrawMass = self.__withdrawMass

  #........................................
  # if the first time step write the header
  #........................................
  if atTime == 0.0:

    assert os.path.isfile(portFile) is False, 'portFile %r exists; stop.' % portFile

    tree = ElementTree.ElementTree()
    rootNode = tree.getroot()

    a = ElementTree.Element('time-variable-packet')
    a.set('name','storage-fuel-segments')

    b = ElementTree.SubElement(a,'comment')
    today = datetime.datetime.today()
    b.set('author','cortix.modules.native.storage')
    b.set('version','0.1')

    b = ElementTree.SubElement(a,'comment')
    today = datetime.datetime.today()
    b.set('today',str(today))

    b = ElementTree.SubElement(a,'time')
    b.set('unit','minute')

    # first packet
    b = ElementTree.SubElement(a,'pack1')
    b.set('name','Geometry')

    for var in vars1:
      c = ElementTree.SubElement(b,'var')
      c.set('name',var[0])
      c.set('unit',var[1])

    # second packet
    b = ElementTree.SubElement(a,'pack2')
    b.set('name','Composition')

    for var in vars2:
      c = ElementTree.SubElement(b,'var')
      c.set('name',var[0])
      c.set('unit',var[1])

    # values for all variables
    b = ElementTree.SubElement(a,'timeStamp')
    b.set('value',str(atTime))

    if withdrawMass == 0.0 or withdrawMass > self.__GetMass( atTime ): 
 
      tree = ElementTree.ElementTree(a)
  
      tree.write( portFile, xml_declaration=True, encoding="unicode", method="xml" )

      s = '__ProvideFuelSegmentsOnDemand(): providing no fuel at '+str(atTime)+' [min]'
      self.__log.debug(s)

      self.__withdrawMass = 0.0

      return

    else: # of if withdrawMass == 0.0 or withdrawMass > self.__GetMass( atTime ): 

      fuelSegmentsLoad = list()
      fuelMassLoad = 0.0

      # withdraw fuel elements
      while fuelMassLoad <= withdrawMass:
           fuelSegmentCandidate = self.__WithdrawFuelSegment( atTime )
           if fuelSegmentCandidate is None: break # no segments left with cut time stamp <= atTime
           mass          = fuelSegmentCandidate[1]
           fuelMassLoad += mass
           if fuelMassLoad <= withdrawMass:
              fuelSegmentsLoad.append( fuelSegmentCandidate )
           else:
              self.__RestockFuelSegment( fuelSegmentCandidate )

      assert len(fuelSegmentsLoad) != 0, 'sanity check failed.'

      # Save in file data from withdrawal
      for fuelSeg in fuelSegmentsLoad:

        cutTimeStamp = fuelSeg[0]
        assert cutTimeStamp <= atTime, 'sanity check failed.'
        mass      = fuelSeg[1]
        length    = fuelSeg[2]
        segID     = fuelSeg[3]
        vol       = length/10.0 * math.pi * segID/10.0*segID/10.0 / 4.0
        dens      = mass / vol
        U         = fuelSeg[4]
        Pu        = fuelSeg[5]
        I         = fuelSeg[6]
        Kr        = fuelSeg[7]
        Xe        = fuelSeg[8]
        a3H       = fuelSeg[9]
        Ru        = fuelSeg[10]
        C         = fuelSeg[11]
        FP        = fuelSeg[12]

        # first packet
        c = ElementTree.SubElement(b,'pack1')
        fuelSegVars1 = [cutTimeStamp,mass,length,segID,vol,dens]
        assert len(fuelSegVars1) == len(vars1)
        for var in fuelSegVars1: 
          s += str(var)+','
        s = s[:-1] 
        c.text = s

        # second packet
        c = ElementTree.SubElement(b,'pack2')
        fuelSegVars2 = [U,Pu,I,Kr,Xe,a3H,FP]
        assert len(fuelSegVars2) == len(vars2)
        for var in fuelSegVars2: 
          s += str(var)+','
        s = s[:-1] 
        c.text = s

        tree = ElementTree.ElementTree(a)
  
        tree.write( portFile, xml_declaration=True, encoding="unicode", method="xml" )
  
        s = '__ProvideFuelSegmentsOnDemand(): providing '+str(len(fuelSegmentsLoad))+' fuel segments at '+str(atTime)+' [min].'
        self.__log.debug(s)

      # endo of for fuelSeg in fuelSegmentsLoad:

      self.__withdrawMass = 0.0

      return

    # end of if withdrawMass == 0.0 or withdrawMass > self.__GetMass( atTime ): 

  #...........................................................................
  # if not the first time step then parse the existing history file and append
  #...........................................................................
  else: # of if atTime == 0.0:

    tree = ElementTree.parse( portFile )
    rootNode = tree.getroot()

    newTimeStamp = ElementTree.Element('timeStamp')
    newTimeStamp.set('value',str(atTime))

    if withdrawMass == 0.0 or withdrawMass > self.__GetMass( atTime ): 

      rootNode.append(newTimeStamp)
      tree.write( portFile, xml_declaration=True, encoding="unicode", method="xml" )

      self.__withdrawMass = 0.0

      s = '__ProvideFuelSegmentsOnDemand(): providing no fuel at '+str(atTime)+' [min]'
      self.__log.debug(s)
   
      return

    else: # of if withdrawMass == 0.0 or withdrawMass > self.__GetMass( atTime ):

      fuelSegmentsLoad = list()
      fuelMassLoad = 0.0

      # withdraw fuel elements
      while fuelMassLoad <= withdrawMass:
           fuelSegmentCandidate = self.__WithdrawFuelSegment( atTime )
           if fuelSegmentCandidate is None: break # no segments left with time stamp <= atTime
           mass          = fuelSegmentCandidate[1]
           fuelMassLoad += mass
           if fuelMassLoad <= withdrawMass:
              fuelSegmentsLoad.append( fuelSegmentCandidate )
           else:
              self.__RestockFuelSegment( fuelSegmentCandidate )

      assert len(fuelSegmentsLoad) != 0, 'sanity check failed.'

      for fuelSeg in fuelSegmentsLoad:

        cutTimeStamp = fuelSeg[0]
        assert cutTimeStamp <= atTime, 'sanity check failed.'
        mass      = round(fuelSeg[1],gDec)
        length    = round(fuelSeg[2],mmDec)
        segID     = round(fuelSeg[3],mmDec)
        vol       = length/10.0 * math.pi * segID/10.0*segID/10.0 / 4.0
        dens      = mass / vol
        U         = round(fuelSeg[4],gDec)
        Pu        = round(fuelSeg[5],gDec)
        I         = round(fuelSeg[6],gDec)
        Kr        = round(fuelSeg[7],gDec)
        Xe        = round(fuelSeg[8],gDec)
        a3H       = round(fuelSeg[9],gDec)
        Ru        = round(fuelSeg[10],gDec)
        C         = round(fuelSeg[11],gDec)
        FP        = round(fuelSeg[12],gDec)
 
        # first packet
        a = ElementTree.SubElement(newTimeStamp, 'pack1')
        fuelSegVars1 = [cutTimeStamp,mass,length,segID,vol,dens]
        assert len(fuelSegVars1) == len(vars1)
        s = ''
        for var in fuelSegVars1: 
          s += str(var)+','
        s = s[:-1] 
        a.text = s

        # second packet
        b = ElementTree.SubElement(newTimeStamp, 'pack2')
        fuelSegVars2 = [U,Pu,I,Kr,Xe,a3H,Ru,C,FP]
        assert len(fuelSegVars2) == len(vars2)
        s = ''
        for var in fuelSegVars2: 
          s += str(var)+','
        s = s[:-1] 
        b.text = s

      rootNode.append(newTimeStamp)
      tree.write( portFile, xml_declaration=True, encoding="unicode", method="xml" )

      s = '__ProvideFuelSegmentsOnDemand(): providing '+str(len(fuelSegmentsLoad))+' fuel segments at '+str(atTime)+' [min].'
      self.__log.debug(s)

      self.__withdrawMass = 0.0

      return

  # end of if atTime == 0.0:

  return

#---------------------------------------------------------------------------------
 def __ProvideState( self, portFile, atTime ):
  
  pyplotScale = 'linear'

  # if the first time step, write the header of a time-sequence data file
  if atTime == 0.0:

    assert os.path.isfile(portFile) is False, 'portFile %r exists; stop.' % portFile

    tree = ElementTree.ElementTree()
    rootNode = tree.getroot()

    a = ElementTree.Element('time-sequence')
    a.set('name','storage-state')

    b = ElementTree.SubElement(a,'comment')
    today = datetime.datetime.today()
    b.set('author','cortix.modules.native.storage')
    b.set('version','0.1')

    b = ElementTree.SubElement(a,'comment')
    today = datetime.datetime.today()
    b.set('today',str(today))

    b = ElementTree.SubElement(a,'time')
    b.set('unit','minute')

    # first variable
    b = ElementTree.SubElement(a,'var')
    b.set('name','Fuel Mass')
    b.set('unit','gram')
    b.set('legend','Storage-state')
    b.set('scale',pyplotScale)

    # second variable
    b = ElementTree.SubElement(a,'var')
    b.set('name','Fuel Segments')
    b.set('unit','')
    b.set('legend','Storage-state')
    b.set('scale',pyplotScale)

    # third variable
    b = ElementTree.SubElement(a,'var')
    b.set('name','Fuel Volume')
    b.set('unit','cc')
    b.set('legend','Storage-state')
    b.set('scale',pyplotScale)

    # fourth variable
    b = ElementTree.SubElement(a,'var')
    b.set('name','U Mass')
    b.set('unit','gram')
    b.set('legend','Storage-state')
    b.set('scale',pyplotScale)

    # fifth variable
    b = ElementTree.SubElement(a,'var')
    b.set('name','Pu Mass')
    b.set('unit','gram')
    b.set('legend','Storage-state')
    b.set('scale',pyplotScale)

    # sixth variable
    b = ElementTree.SubElement(a,'var')
    b.set('name','FP Mass')
    b.set('unit','gram')
    b.set('legend','Storage-state')
    b.set('scale',pyplotScale)

    # seventh variable
    b = ElementTree.SubElement(a,'var')
    b.set('name','Xe Mass')
    b.set('unit','gram')
    b.set('legend','Storage-state')
    b.set('scale',pyplotScale)

    # values for all variables
    b = ElementTree.SubElement(a,'timeStamp')
    b.set('value',str(atTime))

    # all variables values
    gDec   = self.__gramDecimals
    ccDec  = self.__ccDecimals 
    mass   = round(self.__GetMass(),gDec)
    vol    = round(self.__GetFuelVolume(),ccDec)
    uMass  = round(self.__GetUMass(),gDec)
    puMass = round(self.__GetPuMass(),gDec)
    fpMass = round(self.__GetFPMass(),gDec)
    xeMass = round(self.__GetXeMass(),gDec)
    b.text = str(mass)+','+\
             str(self.__GetNSegments())+','+\
             str(vol)+','+\
             str(uMass)+','+\
             str(puMass)+','+\
             str(fpMass)+','+\
             str(xeMass)

    tree = ElementTree.ElementTree(a)

    tree.write( portFile, xml_declaration=True, encoding="unicode", method="xml" )

  # if not the first time step then parse the existing history file and append
  else:

    tree = ElementTree.parse( portFile )
    rootNode = tree.getroot()
    a = ElementTree.Element('timeStamp')
    a.set('value',str(atTime))

    # all variables values
    gDec   = self.__gramDecimals
    ccDec  = self.__ccDecimals 
    mass   = round(self.__GetMass(),gDec)
    vol    = round(self.__GetFuelVolume(),ccDec)
    uMass  = round(self.__GetUMass(),gDec)
    puMass = round(self.__GetPuMass(),gDec)
    fpMass = round(self.__GetFPMass(),gDec)
    xeMass = round(self.__GetXeMass(),gDec)
    a.text = str(mass)+','+\
             str(self.__GetNSegments())+','+\
             str(vol)+','+\
             str(uMass)+','+\
             str(puMass)+','+\
             str(fpMass)+','+\
             str(xeMass)

    rootNode.append(a)

    tree.write( portFile, xml_declaration=True, encoding="unicode", method="xml" )

  return 

#---------------------------------------------------------------------------------
 def __ProvideOffGas( self, portFile, atTime ):

  # if the first time step, write the header of a time-sequence data file
  if atTime == 0.0:

    assert os.path.isfile(portFile) is False, 'portFile %r exists; stop.' % portFile

    tree = ElementTree.ElementTree()
    rootNode = tree.getroot()

    a = ElementTree.Element('time-sequence')
    a.set('name','storage-offgas')

    b = ElementTree.SubElement(a,'comment')
    today = datetime.datetime.today()
    b.set('author','cortix.modules.native.storage')
    b.set('version','0.1')

    b = ElementTree.SubElement(a,'comment')
    today = datetime.datetime.today()
    b.set('today',str(today))

    b = ElementTree.SubElement(a,'time')
    b.set('unit','minute')

    # first variable
    b = ElementTree.SubElement(a,'var')
    b.set('name','Xe Off-Gas')
    b.set('unit','gram/min')
    b.set('legend','Storage-offgas')
    b.set('scale',self.__pyplotScale)

    # second variable
    b = ElementTree.SubElement(a,'var')
    b.set('name','Kr Off-Gas')
    b.set('unit','gram/min')
    b.set('legend','Storage-offgas')
    b.set('scale',self.__pyplotScale)

    # third variable
    b = ElementTree.SubElement(a,'var')
    b.set('name','I2 Off-Gas')
    b.set('unit','gram/min')
    b.set('legend','Storage-offgas')
    b.set('scale',self.__pyplotScale)

    # values for all variables
    b = ElementTree.SubElement(a,'timeStamp')
    b.set('value',str(atTime))
    b.text = str('0.0') + ',' + \
             str('0.0') + ',' + \
             str('0.0')

    tree = ElementTree.ElementTree(a)

    tree.write( portFile, xml_declaration=True, encoding="unicode", method="xml" )

  # if not the first time step then parse the existing history file and append
  else:

    tree = ElementTree.parse( portFile )
    rootNode = tree.getroot()
    a = ElementTree.Element('timeStamp')
    a.set('value',str(atTime))

    # all variables values
    gDec = self.__gramDecimals

    if len(self.__historyXeMassOffGas.keys()) > 0:
      massXe = round( self.__historyXeMassOffGas[ atTime ], gDec )
    else:
      massXe = 0.0

    if len(self.__historyKrMassOffGas.keys()) > 0:
      massKr = round( self.__historyKrMassOffGas[ atTime ], gDec )
    else:
      massKr = 0.0

    if len(self.__historyI2MassOffGas.keys()) > 0:
      massI2 = round( self.__historyI2MassOffGas[ atTime ], gDec )
    else:
      massI2 = 0.0

    a.text = str(massXe) +','+ \
             str(massKr) +','+ \
             str(massI2)

    rootNode.append(a)

    tree.write( portFile, xml_declaration=True, encoding="unicode", method="xml" )

  return 

#---------------------------------------------------------------------------------
 def __GetNSegments(self, timeStamp=None):
 
  nSegments = 0

  if timeStamp is None:
    nSegments = len(self.__fuelSegments)

  else:
     for fuelSeg in self.__fuelSegments:
       if fuelSeg[0] <= timeStamp: nSegments += 1

  return nSegments

#---------------------------------------------------------------------------------
 def __GetFuelVolume(self, timeStamp=None):
 
  volume = 0.0

  if timeStamp is None:
     for fuelSeg in self.__fuelSegments:
      length = fuelSeg[2] 
      iD     = fuelSeg[3]
      volume += length/10.0 * math.pi * iD*iD / 4.0 / 100.0

  else:
     for fuelSeg in self.__fuelSegments:
      if fuelSeg[0] <= timeStamp: 
         length = fuelSeg[2] 
         iD     = fuelSeg[3]
         volume += length/10.0 * math.pi * iD*iD / 4.0 / 100.0

  return volume  # cc unit

#---------------------------------------------------------------------------------
 def __WithdrawFuelSegment(self, atTime ):

  fuelSegment = None

  for fuelSeg in self.__fuelSegments:
    if fuelSeg[0] <= atTime:
      fuelSegment = fuelSeg
      self.__fuelSegments.remove(fuelSeg)
      break 

#  print('WithdrawFuelSegment:: fuelSegment',fuelSegment, ' atTime=',atTime)

  return fuelSegment # if None, it is an empty drum

#---------------------------------------------------------------------------------
 def __RestockFuelSegment( self, fuelSegment ):

  self.__fuelSegments.insert(0,fuelSegment)

#---------------------------------------------------------------------------------
 def __Store( self, facilityTime, timeStep ):

  # Kr, Xe off-gas release; model place holder

  gDec = self.__gramDecimals

  self.__historyXeMassOffGas[facilityTime + timeStep] = 0.0
  self.__historyKrMassOffGas[facilityTime + timeStep] = 0.0
  self.__historyI2MassOffGas[facilityTime + timeStep] = 0.0

  modifiedSegments = list()

  for fuelSeg in self.__fuelSegments:
    cutTimeStamp = fuelSeg[0]
    storageTime = facilityTime - cutTimeStamp
    assert storageTime >= 0.0

    # Xe
    factor = random.random() * 0.1
    massLossFactor = storageTime * factor/100.0/60.0 # rate: 0 to 0.1 wt% per hour of "storage" time
    massLoss = fuelSeg[8] * massLossFactor

    self.__historyXeMassOffGas[ facilityTime + timeStep ] = massLoss

    fuelSeg8 = round(fuelSeg[8] - massLoss,gDec)
    fuelSeg1 = round(fuelSeg[1] - massLoss,gDec)

    # Kr 
    factor = random.random() * 0.1
    massLossFactor = storageTime * factor/100.0/60.0 # rate: 0 to 0.1 wt% per hour of "storage" time
    massLoss = fuelSeg[7] * massLossFactor

    self.__historyKrMassOffGas[ facilityTime + timeStep ] = massLoss

    fuelSeg7 = round(fuelSeg[7] - massLoss,gDec)
    fuelSeg1 = round(fuelSeg1 - massLoss,gDec)

    # I2 
    factor = random.random() * 0.1
    massLossFactor = storageTime * factor/100.0/60.0 # rate: 0 to 0.1 wt% per hour of "storage" time
    massLoss = fuelSeg[6] * massLossFactor

    self.__historyI2MassOffGas[ facilityTime + timeStep ] = massLoss/2.0

    fuelSeg6 = round(fuelSeg[6] - massLoss,gDec)
    fuelSeg1 = round(fuelSeg1 - massLoss,gDec)


    modifiedSegment = ( fuelSeg[0], fuelSeg1,   fuelSeg[2], fuelSeg[3], 
                        fuelSeg[4], fuelSeg[5], fuelSeg6, fuelSeg7, fuelSeg8,
                        fuelSeg[9], fuelSeg[10], fuelSeg[11], fuelSeg[12] )

    self.__fuelSegments.remove(fuelSeg)

    modifiedSegments.append( modifiedSegment )

#    self.__fuelSegments.append(modifiedSegment)

  # end of: for fuelSeg in self.__fuelSegments:

  self.__fuelSegments += modifiedSegments # vfda: may need a deep copy?
  
  assert self.__GetMassCheck() is True, 'mass imbalance; stop.'

  return

#---------------------------------------------------------------------------------
 def __GetMassCheck( self, cutTimeStamp=None ):

  check = True

  gDec = self.__gramDecimals

  if cutTimeStamp is None:
    for fuelSeg in self.__fuelSegments:
      sumMass = 0.0
      for mass in fuelSeg[4:12+1]:
        sumMass += mass
      if abs(round(sumMass,gDec) - round(fuelSeg[1],gDec)) >= 1e-2: 
        print('sum of masses: ',round(sumMass,gDec))
        print('fuelSeg[1]: ',round(fuelSeg[1],gDec))
        print('fuelSegment: ',fuelSeg)
        check = False
        return check
  else:
    for fuelSeg in self.__fuelSegments:
      if fuelSeg[0] <= cutTimeStamp:
        sumMass = 0.0
        for mass in fuelSeg[4:12+1]:
          sumMass += mass
        if abs(round(sumMass,gDec) - round(fuelSeg[1],gDec)) >= 1e-2: 
          print('sum of masses: ',round(sumMass,gDec))
          print('fuelSeg[1]: ',round(fuelSeg[1],gDec))
          print('fuelSegment: ',fuelSeg)
          check = False
          return check

  return check

#*********************************************************************************
# Usage: -> python storage.py
if __name__ == "__main__":
 print('Unit testing for Storage')
