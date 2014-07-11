#!/usr/bin/env python
"""
Valmor F. de Almeida dealmeidav@ornl.gov; vfda

Cortix native FuelAccumulation module

Tue Jun 24 01:03:45 EDT 2014
"""
#*********************************************************************************
import os, sys, io, time, datetime
import logging
import xml.etree.ElementTree as ElementTree
#*********************************************************************************

#*********************************************************************************
class FuelAccumulation(object):

# Private member data
# __slots__ = [

 def __init__( self,
               ports 
             ):

  assert type(ports) is list, '-> ports type %r is invalid.' % type(ports)

  self.__ports = ports

  self.__fuelSegments = list()

  self.__withdrawMass = 0.0

  self.__log = logging.getLogger('fuelaccumulation')
  self.__log.info('initializing an instance of FuelAccumulation')

  self.__gramDecimals   = 3 # milligram significant digits
  self.__mmDecimals = 3 # micrometer significant digits

#---------------------------------------------------------------------------------
 def CallPorts(self, evolTime=0.0):

  self.__UseData( usePortName='solids', evolTime=evolTime  )
 
  self.__UseData( usePortName='withdrawal-request', evolTime=evolTime  )

  self.__ProvideData( providePortName='fuel-segments', evolTime=evolTime )

#---------------------------------------------------------------------------------
 def Execute( self, evolTime=0.0, timeStep=1.0 ):

  s = 'Execute(): facility time [min] = ' + str(evolTime)
  self.__log.info(s)
  s = 'Execute(): total mass [g] = ' + str(round(self.__GetMass(),3))
  self.__log.info(s)
  s = 'Execute(): # of segments  = '+str(len(self.__fuelSegments))
  self.__log.debug(s)

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
 def __UseData( self, usePortName=None, evolTime=0.0 ):

# Access the port file
  portFile = self.__GetPortFile( usePortName = usePortName )

# Get data from port files
  if usePortName == 'solids': self.__GetSolids( portFile, evolTime )

  if usePortName == 'withdrawal-request': self.__GetWithdrawalRequest( portFile, evolTime )

#---------------------------------------------------------------------------------
 def __ProvideData( self, providePortName=None, evolTime=0.0 ):

# Access the port file
  portFile = self.__GetPortFile( providePortName = providePortName )

# Send data to port files
  if providePortName == 'fuel-segments': self.__ProvideFuelSegments( portFile, evolTime )

#---------------------------------------------------------------------------------
 def __GetPortFile( self, usePortName=None, providePortName=None ):

  portFile = None

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

  if providePortName is not None:

    assert usePortName is None

    for port in self.__ports:
     if port[0] == providePortName and port[1] == 'provide': portFile = port[2]

  assert portFile is not None, 'portFile is invalid.'

  return portFile

#---------------------------------------------------------------------------------
# This uses a use portFile which is guaranteed at this point
 def __GetSolids( self, portFile, evolTime ):

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

#  print('mass     [g]= ', mass)
#  print('#segments   = ', nSegments)
#  print('length      = ', segmentLength)
#  print('OD          = ', oD)
#  print('ID          = ', iD)

     FP = totalMass - (U + Pu + I + Kr + Xe + a3H)
#     totalNSegments += nSegments

#  print('mass U      = ', U)
#  print('mass Pu     = ', Pu)
#  print('mass Cs     = ', Cs)
#  print('mass I      = ', I)
#  print('mass O      = ', O)
#  print('mass N      = ', N)
#  print('mass FP     = ', FP)

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

      self.__fuelSegments.append( segment )
  
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

     break

  return

#---------------------------------------------------------------------------------
# This uses a use portFile which is guaranteed to exist at this point
 def __GetWithdrawalRequest( self, portFile, evolTime ):

  found = False

  while found is False:

    s = '__GetWithdrawalRequest(): checking for withdrawal message at '+str(evolTime)
    self.__log.debug(s)

    try:
      tree = ElementTree.parse( portFile )
    except ElementTree.ParseError as error:
      s = '__GetWithdrawalRequest(): '+portFile+' unavailable. Error code: '+str(error.code)+' File position: '+str(error.position)+'. Retrying...'
      self.__log.debug(s)
      continue

    rootNode = tree.getroot()
    assert rootNode.tag == 'time-series', 'invalid format.' 

    node = rootNode.find('time')
    timeUnit = node.get('unit').strip()
    assert timeUnit == "minute"

    # vfda to do: check for single var element
    node = rootNode.find('var')
    assert node.get('name').strip() == 'Fuel Mass Request', 'invalid variable.'
    assert node.get('unit').strip() == 'gram', 'invalid mass unit'

    nodes = rootNode.findall('timeStamp')

    for n in nodes:

      timeStamp = float(n.get('value').strip())
 
      # get data at timeStamp evolTime
      if timeStamp == evolTime:

         found = True

         mass = 0.0
         mass = float(n.text.strip())
         self.__withdrawMass = mass

         s = '__GetWithdrawalRequest(): received withdrawal message at '+str(evolTime)+' [min]; mass [g] = '+str(round(mass,3))
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
# Provide the entire history data 
 def __ProvideFuelSegments( self, portFile, evolTime ):

  gDec = self.__gramDecimals
  mmDec = self.__mmDecimals

  withdrawMass = self.__withdrawMass

  #...........................................
  # if the first time step write a nice header
  #...........................................
  if evolTime == 0.0:

    fout = open( portFile, 'w')

    s = '<?xml version="1.0" encoding="UTF-8"?>\n'; fout.write(s)
    s = '<!-- Written by FuelAccumulation.py -->\n'; fout.write(s)
    today = datetime.datetime.today()
    s = '<!-- '+str(today)+' -->\n'; fout.write(s)

    s = '<fuelsegments>\n'; fout.write(s)
    s = ' <timeStamp value="'+str(evolTime)+'" unit="minute">\n'; fout.write(s)

    if withdrawMass == 0.0 or withdrawMass > self.__GetMass( evolTime ): 

      s = ' </timeStamp>\n'; fout.write(s)
      s = '</fuelsegments>\n'; fout.write(s)
      fout.close()

      self.__withdrawMass = 0.0

      s = '__ProvideFuelSegments(): providing no fuel at '+str(evolTime)+' [min]'
      self.__log.debug(s)

      return

    else: # of if withdrawMass == 0.0 or withdrawMass > self.__GetMass( evolTime ): 

      fuelSegmentsLoad = list()
      fuelMassLoad = 0.0

      # withdraw fuel elements
      while fuelMassLoad <= withdrawMass:
           fuelSegmentCandidate = self.__WithdrawFuelSegment( evolTime )
           if fuelSegmentCandidate is None: break # no segments left with time stamp <= evolTime
           mass          = fuelSegmentCandidate[1]
           fuelMassLoad += mass
           if fuelMassLoad <= withdrawMass:
              fuelSegmentsLoad.append( fuelSegmentCandidate )
           else:
              self.__RestockFuelSegment( fuelSegmentCandidate )

      assert len(fuelSegmentsLoad) != 0, 'sanity check.'

      # Save in file data from withdrawal
      for fuelSeg in fuelSegmentsLoad:

        s = '  <fuelSegment>\n'; fout.write(s)
        timeStamp = fuelSeg[0]
        assert timeStamp <=  evolTime, 'sanity check.'
        mass      = fuelSeg[1]
        length    = fuelSeg[2]
        segID     = fuelSeg[3]
        U         = fuelSeg[4]
        Pu        = fuelSeg[5]
        I         = fuelSeg[6]
        Kr        = fuelSeg[7]
        Xe        = fuelSeg[8]
        a3H       = fuelSeg[9]
        FP        = fuelSeg[10]
        s = '   <timeStamp     unit="minute">'+str(timeStamp)+'</timeStamp>\n'; fout.write(s)
        s = '   <mass          unit="gram">'+str(round(mass,gDec))+'</mass>\n';fout.write(s)
        s = '   <length        unit="mm">'+str(round(length,mmDec))+'</length>\n';fout.write(s)
        s = '   <innerDiameter unit="mm">'+str(round(segID,mmDec))+'</innerDiameter>\n';fout.write(s)
        s = '   <U  unit="gram">'+str(round(U,gDec))+'</U>\n';fout.write(s)
        s = '   <Pu unit="gram">'+str(round(Pu,gDec))+'</Pu>\n';fout.write(s)
        s = '   <I  unit="gram">'+str(round(I,gDec))+'</I>\n';fout.write(s)
        s = '   <Kr unit="gram">'+str(round(Kr,gDec))+'</Kr>\n';fout.write(s)
        s = '   <Xe unit="gram">'+str(round(Xe,gDec))+'</Xe>\n';fout.write(s)
        s = '   <a3H unit="gram">'+str(round(a3H,gDec))+'</a3H>\n';fout.write(s)
        s = '   <FP unit="gram">'+str(round(FP,gDec))+'</FP>\n';fout.write(s)
        s = '  </fuelSegment>\n';      fout.write(s)
  
        s = ' </timeStamp>\n'; fout.write(s)
        s = '</fuelsegments>\n'; fout.write(s)
        fout.close()
 
        s = '__ProvideFuelSegments(): providing '+str(len(fuelSegmentsLoad))+' fuel segments at '+str(evolTime)+' [min].'
        self.__log.debug(s)

      # endo of for fuelSeg in fuelSegmentsLoad:

      return

    # end of if withdrawMass == 0.0 or withdrawMass > self.__GetMass( evolTime ): 

  #...........................................................................
  # if not the first time step then parse the existing history file and append
  #...........................................................................
  else: # of if evolTime == 0.0:

    tree = ElementTree.parse( portFile )
    rootNode = tree.getroot()

    newTimeStamp = ElementTree.Element('timeStamp')
    newTimeStamp.set('value',str(evolTime))
    newTimeStamp.set('unit','minute')

    if withdrawMass == 0.0 or withdrawMass > self.__GetMass( evolTime ): 
 
      rootNode.append(newTimeStamp)
      tree.write( portFile, xml_declaration=True, encoding="unicode", method="xml" )

      self.__withdrawMass = 0.0

      s = '__ProvideFuelSegments(): providing no fuel at '+str(evolTime)+' [min]'
      self.__log.debug(s)
   
      return

    else: 

      fuelSegmentsLoad = list()
      fuelMassLoad = 0.0

      while fuelMassLoad <= withdrawMass:
           fuelSegmentCandidate = self.__WithdrawFuelSegment( evolTime )
           if fuelSegmentCandidate is None: break # no segments left with time stamp <= evolTime
           mass          = fuelSegmentCandidate[1]
           fuelMassLoad += mass
           if fuelMassLoad <= withdrawMass:
              fuelSegmentsLoad.append( fuelSegmentCandidate )
           else:
              self.__RestockFuelSegment( fuelSegmentCandidate )

      assert len(fuelSegmentsLoad) != 0

      for fuelSeg in fuelSegmentsLoad:
#       s = '  <fuelSegment>\n'; fout.write(s)
       newFuelSeg = ElementTree.SubElement(newTimeStamp, 'fuelSegment')
       timeStamp = fuelSeg[0]
       mass      = fuelSeg[1]
       length    = fuelSeg[2]
       segID     = fuelSeg[3]
       U         = fuelSeg[4]
       Pu        = fuelSeg[5]
       I         = fuelSeg[6]
       Kr        = fuelSeg[7]
       Xe        = fuelSeg[8]
       a3H       = fuelSeg[9]
       FP        = fuelSeg[10]
#       s = '   <timeStamp     unit="minute">'+str(timeStamp)+'</timeStamp>\n'; fout.write(s)
       e = ElementTree.SubElement(newFuelSeg, 'timeStamp')
       e.set('unit','minute')
       e.text = str(timeStamp)
#       s = '   <mass          unit="gram">'+str(round(mass,gDec))+'</mass>\n';fout.write(s)
       e = ElementTree.SubElement(newFuelSeg, 'mass')
       e.set('unit','gram')
       e.text = str(round(mass,gDec))
#       s = '   <length        unit="m">'+str(length)+'</length>\n';fout.write(s)
       e = ElementTree.SubElement(newFuelSeg, 'length')
       e.set('unit','mm')
       e.text = str(round(length,mmDec))
#       s = '   <innerDiameter unit="m">'+str(segID)+'</innerDiameter>\n';fout.write(s)
       e = ElementTree.SubElement(newFuelSeg, 'innerDiameter')
       e.set('unit','mm')
       e.text = str(round(segID,mmDec))
#       s = '   <U  unit="gram">'+str(round(U,gDec))+'</U>\n';fout.write(s)
       e = ElementTree.SubElement(newFuelSeg, 'U')
       e.set('unit','gram')
       e.text = str(round(U,gDec))
#       s = '   <Pu unit="gram">'+str(round(Pu,gDec))+'</Pu>\n';fout.write(s)
       e = ElementTree.SubElement(newFuelSeg, 'Pu')
       e.set('unit','gram')
       e.text = str(round(Pu,gDec))
#       s = '   <I  unit="gram">'+str(round(I,gDec))+'</I>\n';fout.write(s)
       e = ElementTree.SubElement(newFuelSeg, 'I')
       e.set('unit','gram')
       e.text = str(round(I,gDec))
#       s = '   <Kr unit="gram">'+str(round(Kr,gDec))+'</Kr>\n';fout.write(s)
       e = ElementTree.SubElement(newFuelSeg, 'Kr')
       e.set('unit','gram')
       e.text = str(round(Kr,gDec))
#       s = '   <Xe unit="gram">'+str(round(Xe,gDec))+'</Xe>\n';fout.write(s)
       e = ElementTree.SubElement(newFuelSeg, 'Xe')
       e.set('unit','gram')
       e.text = str(round(Xe,gDec))
#       s = '   <a3H unit="gram">'+str(round(a3H,gDec))+'</a3H>\n';fout.write(s)
       e = ElementTree.SubElement(newFuelSeg, 'a3H')
       e.set('unit','gram')
       e.text = str(round(a3H,gDec))
#       s = '   <FP unit="gram">'+str(round(FP,gDec))+'</FP>\n';fout.write(s)
       e = ElementTree.SubElement(newFuelSeg, 'FP')
       e.set('unit','gram')
       e.text = str(round(FP,gDec))
#       s = '  </fuelSegment>\n';      fout.write(s)
#      s = ' </timeStamp>\n'; fout.write(s)
#      s = '</fuelsegments>\n'; fout.write(s)
#      fout.close()

      rootNode.append(newTimeStamp)
      tree.write( portFile, xml_declaration=True, encoding="unicode", method="xml" )

      s = '__ProvideFuelSegments(): providing '+str(len(fuelSegmentsLoad))+' fuel segments at '+str(evolTime)+' [min].'
      self.__log.debug(s)

      return

  # end of if evolTime == 0.0:

  return


#---------------------------------------------------------------------------------
# This writes to file only a single time step data at a time
 def __ProvideFuelSegments_DEPRECATED( self, portFile, evolTime ):

  gDec = self.__gramDecimals

  withdrawMass = self.__withdrawMass

  fout = open( portFile, 'w')

  s = '<?xml version="1.0" encoding="UTF-8"?>\n'; fout.write(s)
  s = '<!-- Written by FuelAccumulation.py -->\n'; fout.write(s)
  today = datetime.datetime.today()
  s = '<!-- '+str(today)+' -->\n'; fout.write(s)

  s = '<fuelsegments>\n'; fout.write(s)
  s = ' <timeStamp value="'+str(evolTime)+'" unit="minute">\n'; fout.write(s)

  if withdrawMass == 0.0 or withdrawMass > self.__GetMass( evolTime ): 

   s = ' </timeStamp>\n'; fout.write(s)
   s = '</fuelsegments>\n'; fout.write(s)
   fout.close()
   self.__withdrawMass = 0.0

   s = '__ProvideFuelSegments(): providing no fuel at '+str(evolTime)+' [min]'
   self.__log.debug(s)
   return

  else:  

   fuelSegmentsLoad = list()
   fuelMassLoad = 0.0

   while fuelMassLoad <= withdrawMass:
         fuelSegmentCandidate = self.__WithdrawFuelSegment( evolTime )
         if fuelSegmentCandidate is None: break # no segments left with time stamp <= evolTime
         mass          = fuelSegmentCandidate[1]
         fuelMassLoad += mass
         if fuelMassLoad <= withdrawMass:
            fuelSegmentsLoad.append( fuelSegmentCandidate )
         else:
            self.__RestockFuelSegment( fuelSegmentCandidate )

   assert len(fuelSegmentsLoad) != 0

   for fuelSeg in fuelSegmentsLoad:
    s = '  <fuelSegment>\n'; fout.write(s)
    timeStamp = fuelSeg[0]
    mass      = fuelSeg[1]
    length    = fuelSeg[2]
    segID     = fuelSeg[3]
    U         = fuelSeg[4]
    Pu        = fuelSeg[5]
    I         = fuelSeg[6]
    Kr        = fuelSeg[7]
    Xe        = fuelSeg[8]
    a3H       = fuelSeg[9]
    FP        = fuelSeg[10]
    s = '   <timeStamp     unit="minute">'+str(timeStamp)+'</timeStamp>\n'; fout.write(s)
    s = '   <mass          unit="gram">'+str(round(mass,gDec))+'</mass>\n';fout.write(s)
    s = '   <length        unit="m">'+str(length)+'</length>\n';fout.write(s)
    s = '   <innerDiameter unit="m">'+str(segID)+'</innerDiameter>\n';fout.write(s)
    s = '   <U  unit="gram">'+str(round(U,gDec))+'</U>\n';fout.write(s)
    s = '   <Pu unit="gram">'+str(round(Pu,gDec))+'</Pu>\n';fout.write(s)
    s = '   <I  unit="gram">'+str(round(I,gDec))+'</I>\n';fout.write(s)
    s = '   <Kr unit="gram">'+str(round(Kr,gDec))+'</Kr>\n';fout.write(s)
    s = '   <Xe unit="gram">'+str(round(Xe,gDec))+'</Xe>\n';fout.write(s)
    s = '   <a3H unit="gram">'+str(round(a3H,gDec))+'</a3H>\n';fout.write(s)
    s = '   <FP unit="gram">'+str(round(FP,gDec))+'</FP>\n';fout.write(s)
    s = '  </fuelSegment>\n';      fout.write(s)
 
   s = ' </timeStamp>\n'; fout.write(s)
   s = '</fuelsegments>\n'; fout.write(s)
   fout.close()

   s = '__ProvideFuelSegments(): providing '+str(len(fuelSegmentsLoad))+' fuel segments at '+str(evolTime)+' [min].'
   self.__log.debug(s)

  return

#---------------------------------------------------------------------------------
 def __WithdrawFuelSegment(self, evolTime ):

  fuelSegment = None

  for fuelSeg in self.__fuelSegments:
     if fuelSeg[0] <= evolTime:
      fuelSegment = fuelSeg
      self.__fuelSegments.remove(fuelSeg)
      break 

#  print('WithdrawFuelSegment:: fuelSegment',fuelSegment, ' evolTime=',evolTime)

  return fuelSegment # if None, it is an empty drum

#---------------------------------------------------------------------------------
 def __RestockFuelSegment( self, fuelSegment ):

  self.__fuelSegments.insert(0,fuelSegment)

#*********************************************************************************
# Usage: -> python fuelaccumulation.py
if __name__ == "__main__":
 print('Unit testing for FuelAccumulation')
