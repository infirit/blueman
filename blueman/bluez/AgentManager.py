from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

from blueman.bluez.Base import Base


class AgentManager(Base):
    def __init__(self):
        interface = 'org.bluez.AgentManager1'
        super(AgentManager, self).__init__(interface, '/org/bluez')

    def register_agent(self, agent, capability='', default=False):
        path = agent.get_object_path()
        self._call('RegisterAgent', path, capability)
        if default:
            self._call('RequestDefaultAgent', path)

    def unregister_agent(self, agent):
        self._call('UnregisterAgent', agent.get_object_path())
