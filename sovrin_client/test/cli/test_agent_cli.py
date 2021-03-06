import pytest

from functools import partial

from plenum.test.cli.helper import TestCliCore
from plenum.test.testable import Spyable
from sovrin_client.agent.agent_cli import AgentCli
from sovrin_client.test.agent.acme import createAcme
from sovrin_client.test.cli.helper import getCliBuilder
from sovrin_client.test.cli.test_tutorial import acmeWithEndpointAdded,\
    connectIfNotAlreadyConnected


@Spyable(methods=[AgentCli.print, AgentCli.printTokens])
class TestAgentCLI(AgentCli, TestCliCore):
    pass


@pytest.fixture(scope='module')
def agentCliBuilder(tdir, tdirWithPoolTxns, tdirWithDomainTxns, tconf, cliTempLogger):
    return partial(getCliBuilder, tdir=tdir, tconf=tconf,
                   tdirWithPoolTxns=tdirWithPoolTxns,
                   tdirWithDomainTxns=tdirWithDomainTxns,
                   logFileName=cliTempLogger, cliClass=TestAgentCLI)


@pytest.fixture(scope='module')
def acmeAgentCli(agentCliBuilder, acmeAgentPort):
    yield from agentCliBuilder(
        name='Acme-Agent',
        agentCreator=lambda: createAcme(port=acmeAgentPort)
    )('Acme-Agent')


@pytest.fixture(scope='module')
def acmeAgentCliRunning(acmeWithEndpointAdded, acmeAgentCli, looper):
    looper.run(acmeAgentCli.agent.bootstrap())
    return acmeAgentCli


def test_acme_cli_started_successfully(be, acmeAgentCliRunning):
    be(acmeAgentCliRunning)
    assert acmeAgentCliRunning.currPromptText == 'Acme-Agent'


def sendProofRequest(be, do, agentCli, userMap):
    be(agentCli)
    userMap['pr-name-version'] = '{}-v{}'.format(
        userMap['pr-name'], userMap['pr-schema-version'])
    do('send proof-request {pr-name-version} to {send-proof-target}',
       within=5,
       mapper=userMap,
       expect=[
           'Sent proof request "{pr-name-version}" to {send-proof-target}'
       ])


def checkProofRequestReceived(be, do, userCli, commandMap):
    be(userCli)
    do(None, within=3, mapper=commandMap,
       expect=['Proof request {pr-name} received from {inviter}.'])


def getProofRequestsCount(userCli, target):
    li = userCli.activeWallet.getLinkInvitationByTarget(target)
    return len(li.proofRequests)


@pytest.fixture(scope='module')
def aliceAcceptedAcmeInvitationNoProofReq(
        acmeAgentCliRunning, be, do, aliceCLI, acmeMap, loadInviteOut,
        unsycedAcceptedInviteWithoutClaimOut, connectedToTest,
        syncLinkOutWithEndpoint, newKeyringOut):
    def _(invitationFile, keyring):
        be(aliceCLI)
        connectIfNotAlreadyConnected(do, connectedToTest, aliceCLI, acmeMap)
        keyringMapper = {
            'keyring-name': keyring
        }
        do('new keyring {}'.format(keyring),
           expect=newKeyringOut,
           mapper=keyringMapper)
        do('load {}'.format(invitationFile),
           mapper=acmeMap,
           expect=loadInviteOut)
        do('sync {inviter}',
           mapper=acmeMap,
           expect=syncLinkOutWithEndpoint,
           within=15)
        do('accept invitation from {inviter}',
           within=15,
           mapper=acmeMap,
           expect=unsycedAcceptedInviteWithoutClaimOut)

        proofRequestsBefore = getProofRequestsCount(aliceCLI, acmeMap['target'])

        sendProofRequest(be, do, acmeAgentCliRunning, acmeMap)

        checkProofRequestReceived(be, do, aliceCLI, acmeMap)

        proofRequestsAfter = getProofRequestsCount(aliceCLI, acmeMap['target'])

        return proofRequestsBefore, proofRequestsAfter
    return _


def test_acme_cli_send_proof_request(
        be, do, acmeAgentCliRunning, aliceCLI, acmeMap,
        aliceAcceptedAcmeInvitationNoProofReq):
    proofRequestsBefore, proofRequestsAfter = aliceAcceptedAcmeInvitationNoProofReq(
        acmeMap['invite-no-pr'], 'aliceNoPR')

    assert proofRequestsBefore + 1 == proofRequestsAfter


def test_acme_cli_send_proof_request_already_exist(
        be, do, acmeAgentCliRunning, aliceCLI, acmeMap,
        aliceAcceptedAcmeInvitationNoProofReq):

    proofRequestsBefore, proofRequestsAfter = aliceAcceptedAcmeInvitationNoProofReq(
        acmeMap['invite'], 'aliceWithPR')

    assert proofRequestsBefore == proofRequestsAfter
