#!/usr/bin/python

#    Testing module for REST API code in BDE
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

import time, logging, json, requests, base64, subprocess
import pyVmomi

from pyVmomi import vim
from pyVmomi import vmodl
from pyVim.connect import SmartConnect, Disconnect
from neutronclient.neutron import client

logging.captureWarnings(True)
# - Query node names from BDE through REST API
# - Parse JSON response
# - Query vCenter for VirtualEthernetCard namespace
# - Get MAC address for each node
# - Add port to NSX-v through Neutron for each node.

def get_credentials():
    in_file = "/usr/local/etc/vio.config"
    f = open(in_file, "ro")
    for line in f:
        if "OS_AUTH_URL" in line:
            trash, os_auth_url = map(str, line.split("="))
            os_auth_url = os_auth_url.rstrip('\n')
            print "OS_AUTH_URL:", os_auth_url
        elif "OS_TENANT_ID" in line:
            trash, os_tenant_id = map(str, line.split("="))
            os_tenant_id = os_tenant_id.rstrip('\n')
            print "OS_TENANT_ID:", os_tenant_id
        elif "OS_TENANT_NAME" in line:
            trash, os_tenant_name = map(str, line.split("="))
            os_tenant_name = os_tenant_name.rstrip('\n')
            print "OS_TENANT_NAME:", os_tenant_name
        elif "OS_USERNAME" in line:
            trash, os_username = map(str, line.split("="))
            os_username = os_username.rstrip('\n')
            print "OS_USERNAME:", os_username
        elif "OS_PASSWORD" in line:
            trash, os_password = map(str, line.split("="))
            os_password = os_password.rstrip('\n')
            print "OS_PASSWORD:", os_password
        elif "OS_URL" in line:
            trash, os_url = map(str, line.split("="))
            os_url = os_url.rstrip('\n')
            print "OS_URL:", os_url
        elif "OS_TOKEN" in line:
            trash, os_token = map(str, line.split("="))
            os_token = os_token.rstrip('\n')
            print "OS_TOKEN:", os_token
    d = {}
    d['username'] = os_username
    d['password'] = os_password
    d['auth_url'] = os_auth_url
    d['tenant_name'] = os_tenant_name
    d['token'] = os_token
    d['url'] = os_url
    return d

bde_server = 'bde.localdomain'
vcm_server = 'vcm1.localdomain'
admin_user = 'administrator@vsphere.local'
admin_pass = 'password'
cluster_name = 'mesosphere_stack_01'

header = {'content-type': 'application/x-www-form-urlencoded'}
prefix = 'https://'
port = ':8443'
auth_string = "/serengeti/j_spring_security_check"
data = 'j_username=' + admin_user + '&j_password=' + admin_pass

s = requests.session()
url = prefix + bde_server + port + auth_string
r = s.post(url, data, headers=header, verify=False)

# - Query node names from BDE
header = {'content-type': 'application/json'}
api_call = '/serengeti/api/cluster/' + cluster_name
url = prefix + bde_server + port + api_call
r = s.get(url, headers=header, verify=False)

raw_json = json.loads(r.text)
instance_data = raw_json["nodeGroups"]

# open connection to vCenter
si = SmartConnect(host=vcm_server, user=admin_user, pwd=admin_pass, port=443)
search_index = si.content.searchIndex
root_folder = si.content.rootFolder

security_group = "default"
network = "0559d574-b4a1-4ccd-967a-3bd89bf58e22"
for ng in instance_data:
    vm_data = ng["instances"]
    for vm in vm_data:
        vm_name = vm.get("name")
        vm_moId = vm.get("moId")
        port_name = vm_name + "-port0"

        # the moId looks like: null:VirtualMachine:vm-930
        (x,y,z) = vm_moId.split(":")
        vm_moId = "'vim." + y + ":" + z + "'"

        #DEBUG
        print "BDE Virtual Machine Name: ", vm_name
        print "BDE Virtual Machine moId: ", vm_moId
        #/DEBUG

        # Find specific virtual machine
        for dc in root_folder.childEntity:
            content = si.content
            objView = content.viewManager.CreateContainerView(dc, [vim.VirtualMachine], True)
            vm_list = objView.view
            objView.Destroy()
            for instance in vm_list:
                i = str(instance.summary.vm)
                if vm_moId in i:
                    # VM has been located get the MAC address
                    print "API Virtual Machine Name: ", instance.summary.vm
                    for device in instance.config.hardware.device:
                        if isinstance(device, vim.vm.device.VirtualEthernetCard):
                            mac_address = str(device.macAddress)
                            print "VM MAC Address: ", mac_address
        # NSX bits here
        credentials = get_credentials()
        neutron = client.Client('2.0',
                                username=credentials['username'],
                                password=credentials['password'],
                                auth_url=credentials['auth_url'],
                                tenant_name=credentials['tenant_name'],
                                endpoint_url=credentials['url'],
                                token=credentials['token'])
        port_info = {
                        "port": {
                                "admin_state_up": True,
                                "device_id": vm_name,
                                "name": port_name,
                                "mac_address": mac_address,
                                "network_id": network
                        }
                    }
        response = neutron.create_port(body=port_info)
        print (response)
