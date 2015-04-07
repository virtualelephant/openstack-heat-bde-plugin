#!/usr/bin/python
#
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

import time, json, base64, requests, subprocess

from heat.engine import constraints, properties, resource
from heat.openstack.common import log as logging

logger = logging.getLogger(__name__)

class BigDataExtensions(resource.Resource):

    PROPERTIES = (
        BDE_ENDPOINT, VCM_SERVER, USERNAME, PASSWORD,
        CLUSTER_NAME, CLUSTER_TYPE, CLUSTER_NET, CLUSTER_PASSWORD
    ) = (
        'bde_endpoint', 'vcm_server', 'username', 'password',
        'cluster_name', 'cluster_type', 'cluster_net', 'cluster_password'
    )

    properties_schema = {
        BDE_ENDPOINT: properties.Schema(
            properties.Schema.STRING,
            required=True,
            default='bde.localdomain'
        ),
        VCM_SERVER: properties.Schema(
            properties.Schema.STRING,
            required=True,
            default='vcenter.localdomain'
        ),
        USERNAME: properties.Schema(
            properties.Schema.STRING,
            required=True,
            default='administrator@vsphere.local'
        ),
        PASSWORD: properties.Schema(
            properties.Schema.STRING,
            required=True,
            default='password'
        ),
        CLUSTER_NAME: properties.Schema(
            properties.Schema.STRING,
            required=True
        ),
        CLUSTER_TYPE: properties.Schema(
            properties.Schema.STRING,
            required=True
        ),
        CLUSTER_NET: properties.Schema(
            properties.Schema.STRING,
            required=True
        ),
        CLUSTER_PASSWORD: properties.Schema(
            properties.Schema.STRING,
            required=False
        )
    }

    def _open_connection(self):
        bde_server = self.properties.get(self.BDE_ENDPOINT)
        bde_user = self.properties.get(self.USERNAME)
        bde_pass = self.properties.get(self.PASSWORD)

        header = {'content-type': 'application/x-www-form-urlencoded'}
        prefix = 'https://'
        port = ':8443'
        auth_string = "/serengeti/j_spring_security_check"
        data = 'j_username=' + bde_user + '&j_password=' + bde_pass

        s = requests.session()
        url = prefix + bde_server + port + auth_string
        r = s.post(url, data, headers=header, verify=False)
        logger.info(_("VirtualElephant::VMware::BDE - Authentication status code %s") % r.json)

        return s

    def _close_connection(self):
        bde_server = self.properties.get(self.BDE_ENDPOINT)
        header = {'content-type': 'application/x-www-form-urlencoded'}
        url = 'https://' + bde_server + ':8443/serengeti/j_spring_security_logout'
        s = requests.session()
        r = s.post(url, headers=header, verify=False)
        logger.info(_("VirtualElephant::VMware::BDE - Log out status code %s") % r.json)
    
        return

    def handle_create(self):
        # REST API call to create a new VMware BDE cluster
        bde_server = self.properties.get(self.BDE_ENDPOINT)
        vcm_server = self.properties.get(self.VCM_SERVER)
        bde_user = self.properties.get(self.USERNAME)
        bde_pass = self.properties.get(self.PASSWORD)
        distro = self.properties.get(self.CLUSTER_TYPE)
        name = self.properties.get(self.CLUSTER_NAME)
        network = self.properties.get(self.CLUSTER_NET)
        prefix = 'https://'
        port = ':8443'

        # hack because of Heat sends call before NSX network is created/assigned
        #time.sleep(120)

        # determine actual NSX portgroup created
        # hack - regex in Python is not a strength
        mob_string = '/mob/?moid=datacenter-2'
        curl_cmd = 'curl -k -u ' + bde_user + ':' + bde_pass + ' ' + prefix + vcm_server + mob_string
        grep_cmd = " | grep -oP '(?<=\(vxw).*(?=" + network + "\))' | grep -oE '[^\(]+$'"
        awk_cmd = " | awk '{print $0 \"" + network + "\"}'"
        full_cmd = curl_cmd + grep_cmd + awk_cmd

        p = subprocess.Popen(full_cmd, stdout=subprocess.PIPE, shell=True)
        (net_uid, err) = p.communicate()

        # Check to see if network_id is as we expect it
        if 'vxw' in net_uid:
            network_id = net_uid
        else:
            network_id = "vxw" + net_uid

        network_id = network_id.rstrip('\n')

        # Authenticate in a requests.session to the BDE server
        curr = self._open_connection()

        # Should check to see if network already exists as available network
        # This logs a big fat error message in /opt/serengeti/logs/serengeti.log
        # when the network doesn't exist.
        header = {'content-type': 'application/json'}
        api_call = '/serengeti/api/network/' + network
        url = prefix + bde_server + port + api_call
        r = curr.get(url, headers=header, verify=False)

        # Add new network to BDE as an available network if check fails
        payload = {"name" : network, "portGroup" : network_id, "isDhcp" : "true"}
        api_call = '/serengeti/api/networks'
        url = prefix + bde_server + port + api_call
        r = curr.post(url, data=json.dumps(payload), headers=header, verify=False)
        logger.info(_("VirtualElephant::VMware::BDE - Network creation status code %s") % r.json)

        # Send the create cluster REST API call
        payload = {"name": name, "distro": distro, "networkConfig": { "MGT_NETWORK": [network]}}
        api_call = '/serengeti/api/clusters'
        url = prefix + bde_server + port + api_call
        r = curr.post(url, data=json.dumps(payload), headers=header, verify=False)
        logger.info(_("VirtualElephant::VMware::BDE - Create cluster status code %s") % r.json)

        term = self._close_connection()
        return

    def handle_suspend(self):
        # REST API call to shutdown an existing VMware BDE cluster
        bde_server = self.properties.get(self.BDE_ENDPOINT)
        bde_user = self.properties.get(self.USERNAME)
        bde_pass = self.properties.get(self.PASSWORD)
        name = self.properties.get(self.CLUSTER_NAME)
        prefix = 'https://'
        port = ':8443'
        state = 'stop'

        curr = self._open_connection()
        header = {'content-type': 'application/json'}
        api_call = '/serengeti/api/cluster/' + name + '?state=' + state
        url = prefix + bde_server + port + api_call
        r = curr.post(url, headers=header, verify=False)
        logger.info(_("VirtualElephant::VMware::BDE - Stop cluster status code %s") % r.json)

        term = self._close_connection()
        return

    def handle_resume(self):
        # REST API call to startup an existing VMware BDE cluster
        bde_server = self.properties.get(self.BDE_ENDPOINT)
        bde_user = self.properties.get(self.USERNAME)
        bde_pass = self.properties.get(self.PASSWORD)
        name = self.properties.get(self.CLUSTER_NAME)
        prefix = 'https://'
        port = ':8443'
        state = 'start'

        curr = self._open_connection()
        header = {'content-type': 'application/json'}
        api_call = '/serengeti/api/cluster/' + name + '?state=' + state
        url = prefix + bde_server + port + api_call
        r = curr.post(url, headers=header, verify=False)
        logger.info(_("VirtualElephant::VMware::BDE - Start cluster status code %s") % r.json)

        term = self._close_connection()
        return

    def handle_delete(self):
        # REST API call to delete an existing VMware BDE cluster
        bde_server = self.properties.get(self.BDE_ENDPOINT)
        bde_user = self.properties.get(self.USERNAME)
        bde_pass = self.properties.get(self.PASSWORD)
        name = self.properties.get(self.CLUSTER_NAME)
        prefix = 'https://'
        port = ':8443'

        curr = self._open_connection()
        header = {'content-type': 'application/json'}
        api_call = '/serengeti/api/cluster/' + name
        url = prefix + bde_server + port + api_call
        r = curr.delete(url, headers=header, verify=False)
        logger.info(_("VirtualElephant::VMware::BDE - Delete cluster status code %s") % r.json)

        term = self._close_connection()
        return

def resource_mapping():
    return { 'VirtualElephant::VMware::BDE': BigDataExtensions }
