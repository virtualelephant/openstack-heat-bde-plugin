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

import subprocess

vcm_server = "vcenter.localdomain"
bde_user = "administrator@vsphere.local"
bde_pass = "password"
prefix = "https://"
port = ":8443"

network = "bb16bc26-7faf-4a93-b86f-402870bf5d69"
mob_string = '/mob/?moid=datacenter-2'
curl_cmd = 'curl -k -u ' + bde_user + ':' + bde_pass + ' ' + prefix + vcm_server + mob_string
grep_cmd = " | grep -oP '(?<=\(vxw).*(?=" + network + "\))'"
awk_cmd = " | awk '{print \"vxw\" $0 \"" + network + "\"}'"
full_cmd = curl_cmd + grep_cmd + awk_cmd
p = subprocess.Popen(full_cmd, stdout=subprocess.PIPE, shell=True)
(network_id, err) = p.communicate()

print network_id
