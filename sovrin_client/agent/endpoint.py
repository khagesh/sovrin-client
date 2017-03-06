from typing import Callable, Any, List

from plenum.common.log import getlogger
from plenum.common.raet import getHaFromLocalEstate
from plenum.common.stacked import KITStack
from plenum.common.types import HA
from plenum.common.util import randomString
from raet.raeting import AutoMode
from raet.road.estating import RemoteEstate

logger = getlogger()


class Endpoint(KITStack):
    def __init__(self, port: int, msgHandler: Callable,
                 name: str=None, basedirpath: str=None):
        if name and basedirpath:
            ha = getHaFromLocalEstate(name, basedirpath)
            if ha and ha[1] != port:
                port = ha[1]

        stackParams = {
            "name": name or randomString(8),
            "ha": HA("0.0.0.0", port),
            "main": True,
            "auto": AutoMode.always,
            "mutable": "mutable"
        }
        if basedirpath:
            stackParams["basedirpath"] = basedirpath

        self.registry = {}
        super().__init__(stackParams, self.baseMsgHandler, self.registry)

        self.msgHandler = msgHandler

    def transmitToClient(self, msg: Any, remoteName: str):
        """
        Transmit the specified message to the remote client specified by
         `remoteName`.
        :param msg: a message
        :param remoteName: the name of the remote
        """
        # At this time, nodes are not signing messages to clients, beyond what
        # happens inherently with RAET
        payload = self.prepForSending(msg)
        try:
            self.send(payload, remoteName)
        except Exception as ex:
            logger.error("{} unable to send message {} to client {}; "
                         "Exception: {}".format(self.name, msg, remoteName,
                                               ex.__repr__()))

    def transmitToClients(self, msg: Any, remoteNames: List[str]):
        for nm in remoteNames:
            self.transmitToClient(msg, nm)

    # TODO: Rename method
    def baseMsgHandler(self, msg):
        logger.debug("Got {}".format(msg))
        self.msgHandler(msg)

    def connectTo(self, ha):
        remote = self.findInRemotesByHA(ha)
        if not remote:
            while True:
                name = randomString(8)
                if name in self.registry: continue
                else: break

            self.registry[name] = ha
            self.connect(name)
