# -*- coding: utf-8 -*-
# This file is part of the Cortix toolkit evironment
# https://github.com/dpploy/...
#
# All rights reserved, see COPYRIGHT for full restrictions.
# https://github.com/dpploy/COPYRIGHT
#
# Licensed under the GNU General Public License v. 3, please see LICENSE file.
# https://www.gnu.org/licenses/gpl-3.0.txt
"""
Application class for Cortix.

Cortix: a program for system-level modules coupling, execution, and analysis.
"""
#*********************************************************************************
import os
import sys
import logging
from cortix.src.utils.configtree import ConfigTree
from cortix.src.utils.set_logger_level import set_logger_level
from cortix.src.module import Module
from cortix.src.network import Network
#*********************************************************************************

class Application:
    r"""
    An Application is a singleton class composed of Module objects, and Network
    objects; the latter involve Module objects in various combinations. Each
    combination is assigned to a Network object.

    Attributes
    ----------
     networks: list(str)
         List of names of network objects.
     network: `Network`
         Network object.
     modules: list(str)
         List of names of Cortix Module objects.
     module: `Module`
         Cortix Module object.

    Note
    ----
      Add type annotation to all methods?

      Here is some math:

      .. math::
          k = \alpha\,e^{-\frac{\Delta G}{R T}}
    """

    def __init__(self, app_work_dir=None, app_config_node=ConfigTree()):

        assert isinstance(app_work_dir, str), "-> app_work_dir is invalid"

        # Inherit a configuration tree
        assert isinstance(app_config_node, ConfigTree), "-> app_config_node invalid"
        assert isinstance(app_config_node.get_node_tag(), str), "empty xml tree."
        self.config_node = app_config_node

        # Read the application name
        self.name = self.config_node.get_node_name()

        # Set the work directory (previously created)
        self.work_dir = app_work_dir
        assert os.path.isdir(app_work_dir), "Work directory not available."

        # Set the module library for the whole application
        node = app_config_node.get_sub_node('module_library')
        self.module_lib_name = node.get("name").strip()
        sub_node = ConfigTree(node)
        assert sub_node.get_node_tag() == "module_library", "FATAL."
        for child in sub_node.get_node_children():
            (elem, tag, attributes, text) = child
            if tag == 'parent_dir':
                self.module_lib_full_parent_dir = text.strip()

        if self.module_lib_full_parent_dir[-1] == '/':
            self.module_lib_full_parent_dir.strip('/')

        # add library full path to python module search
        sys.path.insert(1, self.module_lib_full_parent_dir)

        # Create the logging facility for the singleton object
        node = app_config_node.get_sub_node("logger")
        logger_name = self.name + ".app" # postfix to avoid clash of loggers
        self.log = logging.getLogger(logger_name)
        self.log.setLevel(logging.NOTSET)

        logger_level = node.get("level").strip()
        self.log = set_logger_level(self.log, logger_name, logger_level)

        file_handler = logging.FileHandler(self.work_dir + "app.log")
        file_handler.setLevel(logging.NOTSET)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.NOTSET)

        for child in node:
            if child.tag == 'file_handler':
                # file handler
                file_handler_level = child.get('level').strip()
                file_handler = set_logger_level(file_handler, logger_name, \
                                                file_handler_level)
            if child.tag == 'console_handler':
                # console handler
                console_handler_level = child.get('level').strip()
                console_handler = set_logger_level(console_handler, logger_name,
                                                   console_handler_level)

        # formatter added to handlers
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # add handlers to logger
        self.log.addHandler(file_handler)
        self.log.addHandler(console_handler)
        self.log.info("Created Application logger: %s", self.name)
        self.log.debug("logger level: %s", logger_level)
        self.log.debug("logger file handler level: %s", file_handler_level)
        self.log.debug("logger console handler level: %s", console_handler_level)

        self.modules = list()
        self.__setup_modules()

        self.networks = list()
        self.__setup_networks()

        self.log.info("Created application: %s", self.name)
#---------------------- end def __init__():---------------------------------------

    def get_networks(self):
        """
        Returns a list of the application's networks.
        """

        return self.networks
#---------------------- end def get_networks():-----------------------------------

    def get_network(self, name):
        """
        Returns a network with a given name.  None if the name doesn't exist.
        """

        for net in self.networks:
            if net.get_name() == name:
                return net
        return None
#---------------------- end def get_network():------------------------------------

    def get_modules(self):
        """
        Returns a list of the application's modules
        """

        return self.modules
#---------------------- end def get_modules():------------------------------------

    def get_module(self, name):
        """
        Returns a module with a given name.  None if the name doesn't exist.
        """
        for mod in self.modules:
            if mod.get_name() == name:
                return mod
        return None
#---------------------- end def get_module():-------------------------------------

    def __del__(self):

        self.log.info("destroyed application: %s", self.name)
#---------------------- end def __del__():----------------------------------------

#*********************************************************************************
# Private helper functions (internal use: __)

    def __setup_networks(self):
        """
        A helper function used by the Application constructor to setup the networks
        portion of the Application.
        """

        self.log.debug("start _SetupNetworks()")

        for net_node in self.config_node.get_all_sub_nodes("network"):
            net_config_node = ConfigTree(net_node)
            assert net_config_node.get_node_name() == net_node.get('name'), 'check failed'
            network = Network(net_config_node)
            self.networks.append(network)
            self.log.debug("appended network %s", net_node.get("name"))

        self.log.debug("end _SetupNetworks()")
#---------------------- end def __setup_networks():-------------------------------

    def __setup_modules(self):
        """
        A helper function used by the Application constructor to setup the modules
        portion of the Application.
        """

        self.log.debug("Start _SetupModules()")
        for mode_node in self.config_node.get_all_sub_nodes('module'):

            mod_config_node = ConfigTree(mode_node)
            assert mod_config_node.get_node_name() == mode_node.get('name'), \
            'check failed'

            new_module = Module(self.work_dir, self.module_lib_name,
                                self.module_lib_full_parent_dir, mod_config_node)

            # check for a duplicate module before appending a new one
            for module in self.modules:
                mod_name = module.get_name()
                mod_lib_dir_name = module.get_library_parent_dir()
                mod_lib_name = module.get_library_name()

                if new_module.get_name() == mod_name:
                    if new_module.get_library_parent_dir() == mod_lib_dir_name:
                        assert new_module.get_library_name != mod_lib_name, \
                        "duplicate module; ABORT."

            # add module to list
            self.modules.append(new_module)
            self.log.debug("appended module %s", mode_node.get('name'))

        self.log.debug("end _SetupModules()")
#---------------------- end def __setup_modules():--------------------------------

#====================== end class Application: ===================================
