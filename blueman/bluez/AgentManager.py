from __future__ import print_function
from __future__ import division
from __future__ import absolute_import
from __future__ import unicode_literals

from blueman.bluez.Base import Base


class AgentManager(Base):
    def __init__(self):
        super(AgentManager, self).__init__(
            interface_name='org.bluez.AgentManager1', obj_path='/org/bluez')

    def register_agent(self, agent, capability='', default=False):
        path = agent.get_object_path()
        self._call('RegisterAgent', 'os', path, capability)
        if default:
            self._call('RequestDefaultAgent', 'o', path)

    def unregister_agent(self, agent):
        self._call('UnregisterAgent', 'o', agent.get_object_path())
