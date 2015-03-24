#    OpenStack Heat Plugin for interfacing with VMware Big Data Extensions
#
#    Chris Mutchler - chris@virtualelephant.com
#    http://www.VirtualElephant.com
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import time, json, base64, requests
requests.packages.urllib3.disable_warnings()

from heat.common.i18n import _
from heat.engine import constraints, properties, resource
from heat.openstack.common.gettextutils import _
from heat.openstack.common import log as logging

logger = logging.getLogger(__name__)

class BigDataExtensions(resource.Resource):

    PROPERTIES = (
        BDE_ENDPOINT, USERNAME, PASSWORD,
        CLUSTER_NAME, CLUSTER_TYPE, CLUSTER_NET, CLUSTER_PASSWORD
    ) = (
        'bde_endpoint', 'username', 'password',
        'cluster_name', 'cluster_type', 'cluster_net', 'cluster_password'
    )

    properties_schema = {
        BDE_ENDPOINT: properties.Schema(
            properties.Schema.STRING,
            _('The hostname or IP address of the VMware BDE Management Server'),
            required=True,
            default='127.0.0.1'
        ),
        USERNAME: properties.Schema(
            properties.Schema.STRING,
            _('The username to the vCenter VMware BDE Management server is connected to'),
            required=True,
            default='administrator@vsphere.local'
        ),
        PASSWORD: properties.Schema(
            properties.Schema.STRING,
            _('The password to the vCenter.'),
            required=True,
            default='vmware'
        ),
        CLUSTER_NAME: properties.Schema(
            properties.Schema.STRING,
            _('The user-defined cluster name'),
            required=True
            # Should add constraints here that match the BDE constraints on the cluster names
        ),
        CLUSTER_TYPE: properties.Schema(
            properties.Schema.STRING,
            _('The cluster type to deploy through BDE (Hadoop|Mesos|Storm|Kafka|Cassandra'),
            required=True
        ),
        CLUSTER_NET: properties.Schema(
            properties.Schema.STRING,
            _('The network to deploy the cluster onto'),
            required=True
        ),
        CLUSTER_PASSWORD: properties.Schema(
            properties.Schema.STRING,
            _('The password to assign to the cluster nodes'),
            required=False
        )
    }

    attributes_schema = {
        'bleh': _('unknown variable')
    }

    def _get_bde_server(self):
        endpoint = self.properties.get(self.BDE_ENDPOINT)
        username = self.properties.get(self.USERNAME)
        password = self.properties.get(self.PASSWORD)
        logger.debug(_("_get_bde_server bde_endpoint=%s, username=%s") % (endpoint, username))
        return (
            bde_endpoint=endpoint,
            username=username,
            password=password
        )

    def handle_create(self):
        _bde_server = self._get_bde_server()
        logger.debug(_("BDE servers %s") % _bde_server.list())

        # setup the cluster information
        _cluster_description = {
            'name': self.properties.get(self.CLUSTER_NAME),
            'type': self.properties.get(self.CLUSTER_TYPE),

            # Check to see if a cluster password was set
            if self.properties.get(self.CLUSTER_PASSWORD):
                'passwd': self.properties.get(self.CLUSTER_PASSWORD)
        } #/END setup cluster information
        logger.debug(_("The cluster should be setup with the following %s") % _cluster_description)

        # Authenticate in a requests.session to the BDE server
        header = {'content-type': 'application/x-www-form-urlencoded'}
        prefix = 'https://'
        port = ':8443'
        auth_string = "/serengeti/j_spring_security_check"
        data = 'j_username=' + username + '&j_password=' + password

        # Setup the session
        s = requests.session()
        url = prefix + bde_endpoint + port + auth_string
        r = s.post(url, data, headers=header, verify=False)
        logger.debug(_("Authentication status code %s") % r.json)

        # Now that we have authenticated, send REST API call
        header = {'content-type': 'application/json'}
        payload = {"name": clusterName, "distro": clusterType, "networkConfig": { "MGT_NETWORK": ["defaultNetwork"]}}
        api_call = '/serengeti/api/clusters'
        url = prefix + bde_endpoint + port + api_call
        r = s.post(url, data=json.dumps(payload), headers=header, verify=False)
        logger.debug(_("REST API call status code %s") % r.json)

        return

    def handle_suspend(self):
        # Call to shutdown the cluster through REST API
        _bde_server = self._get_bde_server()
        logger.debug(_("BDE management server %s") % _bde_server.list())

        _cluster_description = {
            'name': self.properties.get(self.CLUSTER_NAME)
        } #/END _cluster_description
        logger.debug(_("The %s cluster will be shutdown") % _cluster_description)

        # Authenticate in a requests.session to the BDE server
        header = {'content-type': 'application/x-www-form-urlencoded'}
        prefix = 'https://'
        port = ':8443'
        auth_string = "/serengeti/j_spring_security_check"
        data = 'j_username=' + username + '&j_password=' + password
        clusterState = "stop"

        # Setup session
        s = requests.session()
        url = prefix + bde_endpoint + port + auth_string
        r = s.post(url, data, headers=header, verify=False)
        logger.debug(_("Authentication status code %s") % r.json)

        # REST API call to shutdown cluster
        header = {'content-type': 'application/json'}
        api_call = '/serengeti/api/cluster/' + clusterName + '?state=' + clusterState
        url = prefix + bde_endpoint + port + api_call
        r = s.put(url, headers=header, verify=False)
        logger.debug(_("REST API stop call status code %s") % r.json)

        return

    def handle_resume(self):
        # Call to start the cluster through REST API
        _bde_server = self._get_bde_server()
        logger.debug(_("BDE management server %s") % _bde_server.list())

        _cluster_description = {
            'name': self.properties.get(self.CLUSTER_NAME)
        } #/END _cluster_description

        # Authenticate
        header = {'content-type': 'application/x-www-form-urlencoded'}
        prefix = 'https://'
        port = ':8443'
        auth_string = "/serengeti/j_spring_security_check"
        data = 'j_username=' + username + '&j_password=' + password
        clusterState = "start"

        # Setup session
        s = requests.session()
        url = prefix + bde_endpoint + port + auth_string
        r = s.post(url, data, headers=header, verify=False)
        logger.debug(_("Authentication status code %s") % r.json)

        # REST API call to start cluster
        header = {'content-type': 'application/json'}
        payload = {"state": clusterState}
        api_call = '/serengeti/api/cluster/' + clusterName
        url = prefix + bde_endpoint + port + api_call
        r = s.put(url, data=json.dumps(payload), headers=header, verify=False)
        logger.debug(_("REST API start call status code %s") % r.json)

        return

    def handle_delete(self):
        # Call to delete the cluster through REST API
        _bde_server = self._get_bde_server()
        logger.debug(_("BDE management server %s") % _bde_server.list())

        _cluster_description = {
            'name': self.properties.get(self.CLUSTER_NAME)
        } #/END _cluster_description

        # Authenticate
        header = {'content-type': 'application/x-www-form-urlencoded'}
        prefix = 'https://'
        port = ':8443'
        auth_string = "/serengeti/j_spring_security_check"
        data = 'j_username=' + username + '&j_password=' + password

        # Setup session
        s = requests.session()
        url = prefix + bde_endpoint + port + auth_string
        r = s.post(url, data, headers=header, verify=False)
        logger.debug(_("Authentication status code %s") % r.json)

        # REST API call to delete cluster
        header = {'content-type': 'application/json'}
        api_call = '/serengeti/api/cluster/' + clusterName
        url = prefix + bde_endpoint + port + api_call
        r = s.delete(url, headers=header, verify=False)
        logger.debug(_("REST API delete call status code %s") % r.json)
        

        return

def resource_mapping():
    return {
        'VirtualElephant::BigDataExtensions': BigDataExtensions
    }
