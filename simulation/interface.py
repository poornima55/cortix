#!/usr/bin/env python
"""
Author: Valmor F. de Almeida dealmeidav@ornl.gov; vfda

Cortix: a program for system-level modules
        coupling, execution, and analysis.

Tue Dec 10 11:21:30 EDT 2013
"""
#*********************************************************************************
import os, sys, io
from cortix.utils.configtree import ConfigTree
from cortix.application.interface import Application

# constructor helper
from ._simulation import _Simulation

from ._execute import _Execute
#*********************************************************************************

#*********************************************************************************
class Simulation():

 def __init__( self,
               parentWorkDir = None,
               simConfigNode = ConfigTree()
             ):

  _Simulation( self, parentWorkDir, simConfigNode )

  return

 def __del__( self ):

  s = 'destroyed simulation: '+self.name
  self.log.info(s)

  return

#---------------------------------------------------------------------------------
# Execute  

 def Execute( self, taskName=None ):

  _Execute( self, taskName )

  return

#*********************************************************************************
# Unit testing. Usage: -> python simulation.py
if __name__ == "__main__":
  print('Unit testing for Simulation')
