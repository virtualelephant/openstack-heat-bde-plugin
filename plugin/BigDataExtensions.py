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

import time
import json
import base64
import requests
import subprocess
import pyVmomi

from pyVim import connect
from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vmodl, vim
from heat.engine import constraints, properties, resource
from heat.openstack.common import log as logging
from neutronclient.neutron import client

logger = logging.getLogger(__name__)

class BigDataExtensions(resource.Resource):

    PROPERTIES = (
        BDE_ENDPOINT, VCM_SERVER, USERNAME, PASSWORD,
        CLUSTER_NAME, CLUSTER_TYPE, NETWORK, CLUSTER_PASSWORD, CLUSTER_RP,
        VIO_CONFIG, BDE_CONFIG, SECURITY_GROUP, SUBNET
    ) = (
        'bde_endpoint', 'vcm_server', 'username', 'password',
        'cluster_name', 'cluster_type', 'network', 'cluster_password', 'cluster_rp',
        'vio_config', 'bde_config', 'security_group', 'subnet'
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
        NETWORK: properties.Schema(
            properties.Schema.STRING,
            required=True
        ),
        CLUSTER_PASSWORD: properties.Schema(
            properties.Schema.STRING,
            required=False
        ),
        CLUSTER_RP: properties.Schema(
            properties.Schema.STRING,
            required=True,
            default='openstackRP'
        ),
        VIO_CONFIG: properties.Schema(
            properties.Schema.STRING,
            required=True,
            default='/usr/local/bin/etc/vio.config'
        ),
        BDE_CONFIG: properties.Schema(
            properties.Schema.STRING,
            required=False,
            default='/usr/local/bin/etc/bde.config'
        ),
        SECURITY_GROUP: properties.Schema(
            properties.Schema.STRING,
            required=False,
            default='9d3ecec8-e0e3-4088-8c71-8c35cd67dd8b'
        ),
        SUBNET: properties.Schema(
            properties.Schema.STRING,
            required=True
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

    def _create_nsx_ports(self):
        # Load VIO environment variables from /usr/local/etc/vio.config
        in_file = "/usr/local/etc/vio.config"
        f = open(in_file, "ro")
        for line in f:
            if "OS_AUTH_URL" in line:
                trash, os_auth_url = map(str, line.split("="))
                os_auth_url = os_auth_url.rstrip('\n')
                logger.info(_("VirtualElephant::VMware::BDE - DEBUG os_auth_url %s") % os_auth_url)
            elif "OS_TENANT_ID" in line:
                trash, os_tenant_id = map(str,line.split("="))
                os_tenant_id = os_tenant_id.rstrip('\n')
            elif "OS_TENANT_NAME" in line:
                trash, os_tenant_name = map(str, line.split("="))
                os_tenant_name = os_tenant_name.rstrip('\n')
            elif "OS_USERNAME" in line:
                trash, os_username = map(str, line.split("="))
                os_username = os_username.rstrip('\n')
            elif "OS_PASSWORD" in line:
                trash, os_password = map(str, line.split("="))
                os_password = os_password.rstrip('\n')
            elif "OS_URL" in line:
                trash, os_url = map(str, line.split("="))
                os_url = os_url.rstrip('\n')
            elif "OS_TOKEN" in line:
                trash, os_token = map(str, line.split("="))
                os_token = os_token.rstrip('\n')

        d = {}
        d['username'] = os_username
        d['password'] = os_password
        d['auth_url'] = os_auth_url
        d['tenant_name'] = os_tenant_name
        d['token'] = os_token
        d['url'] = os_url

        logger.info(_("VirtualElephant::VMware::BDE - Loaded VIO credentials - %s") % d)

        # Using BDE API and vSphere API return the MAC address
        # for the virtual machines created by BDE.
        bde_server = self.properties.get(self.BDE_ENDPOINT)
        vcm_server = self.properties.get(self.VCM_SERVER)
        admin_user = self.properties.get(self.USERNAME)
        admin_pass = self.properties.get(self.PASSWORD)
        cluster_name = self.properties.get(self.CLUSTER_NAME)
        network_id = self.properties.get(self.NETWORK)
        security_group = self.properties.get(self.SECURITY_GROUP)

        prefix = 'https://'
        port = ':8443'

        logger.info(_("VirtualElephant::VMware::BDE - Creating NSX ports for network %s") % network_id)

        # Get the node names for the cluster from BDE
        curr = self._open_connection()
        header = {'content-type': 'application/json'}
        api_call = '/serengeti/api/cluster/' + cluster_name
        url = prefix + bde_server + port + api_call
        r = curr.get(url, headers=header, verify=False)
        raw_json = json.loads(r.text)
        cluster_data = raw_json["nodeGroups"]

        # Open connect to the vSphere API
        si = SmartConnect(host=vcm_server, user=admin_user, pwd=admin_pass, port=443)
        search_index = si.content.searchIndex
        root_folder = si.content.rootFolder
        for ng in cluster_data:
            nodes = ng["instances"]
            for node in nodes:
                logger.info(_("VirtualElephant::VMware::BDE - Creating NSX port for %s") % node.get("name"))
                vm_name = node.get("name")
                vm_moId = node.get("moId")
                port_name = vm_name + "-port0"
                
                # moId is not in format we need to match
                (x,y,z) = vm_moId.split(":")
                vm_moId = "'vim." + y + ":" + z + "'"

                # Go through each DC one at a time, in case there are multiple in vCenter
                for dc in root_folder.childEntity:
                    content = si.content
                    objView = content.viewManager.CreateContainerView(dc, [vim.VirtualMachine], True)
                    vm_list = objView.view
                    objView.Destroy()
                    
                    for instance in vm_list:
                        # convert object to string so we can search
                        i = str(instance.summary.vm)
                        if vm_moId in i:
                            # Matched the VM in BDE and vCenter
                            logger.info(_("VirtualElephant::VMware::BDE - Match found for BDE node %s") % instance)
                            for device in instance.config.hardware.device:
                                if isinstance(device, vim.vm.device.VirtualEthernetCard):
                                    mac_address = str(device.macAddress)
                                    logger.info(_("VirtualElephant::VMware::BDE - Found MAC address %s") % mac_address)

                        # If the node is already trying to get an IP address,
                        # then a powercycle is required.
                        #logger.info(_("VirtualElephant::VMware::BDE - Powercycling the node %s") % node.get("name"))
                        #if instance.runtime.powerState == vim.VirtualMachinePowerState.poweredOn:
                        #    task = instance.PowerOff()
                        #    while task.info.state not in [vim.TaskInfo.State.success,
                        #                                  vim.TaskInfo.State.error]:
                        #        logger.info(_("VirtualElephant::VMware::BDE - Waiting for node power off %s") % node.get("name"))
                        #        time.sleep(5)
                        #    task = instance.PowerOn()
                        #    while task.info.state not in [vim.TaskInfo.State.success,
                        #                                  vim.TaskInfo.State.error]:
                        #        logger.info(_("VirtualElephant::VMware::BDE - Waiting for node power on %s") % node.get("name"))
                        #        time.sleep(5)

                # Create a new port through Neutron
                neutron = client.Client('2.0',
                                        username=os_username,
                                        password=os_password,
                                        auth_url=os_auth_url,
                                        tenant_name=os_tenant_name,
                                        endpoint_url=os_url,
                                        token=os_token)
                port_info = {
                                "port": {
                                        "admin_state_up": True,
                                        "device_id": vm_name,
                                        "name": port_name,
                                        "mac_address": mac_address,
                                        "network_id": network_id
                                }
                            }
                logger.info(_("VirtualElephant::VMware::BDE - Neutron port string %s") % port_info)

                response = neutron.create_port(body=port_info)
                logger.info(_("VirtualElephant::VMware::BDE - NSX port creation response - %s") % response)
        return

    def handle_create(self):
        # REST API call to create a new VMware BDE cluster
        bde_server = self.properties.get(self.BDE_ENDPOINT)
        vcm_server = self.properties.get(self.VCM_SERVER)
        bde_user = self.properties.get(self.USERNAME)
        bde_pass = self.properties.get(self.PASSWORD)
        distro = self.properties.get(self.CLUSTER_TYPE)
        clusterName = self.properties.get(self.CLUSTER_NAME)
        network = self.properties.get(self.NETWORK)
        rp = self.properties.get(self.CLUSTER_RP)
        prefix = 'https://'
        port = ':8443'

        # hack because of Heat sends call before NSX network is created/assigned
        #time.sleep(60)

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
        payload = {"name": clusterName, "distro": distro, "rpNames": [rp],  "networkConfig": { "MGT_NETWORK": [network]}}
        api_call = '/serengeti/api/clusters'
        url = prefix + bde_server + port + api_call
        r = curr.post(url, data=json.dumps(payload), headers=header, verify=False)
        logger.info(_("VirtualElephant::VMware::BDE - Create cluster status code %s") % r.json)

        # Arbitrary sleep value to allow for the nodes to be cloned
        sleep = 180
        logger.info(_("VirtualElephant::VMware::BDE - Sleeping for %s seconds BDE to create nodes") % sleep)
        time.sleep(sleep)
        # Create ports for the BDE nodes on the NSX logical router
        nsx = self._create_nsx_ports()

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

        # Need to delete the NSX ports for clean-up

        term = self._close_connection()
        return

def resource_mapping():
    return { 'VirtualElephant::VMware::BDE': BigDataExtensions }
