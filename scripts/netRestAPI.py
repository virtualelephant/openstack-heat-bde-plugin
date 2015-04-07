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

import time, json, base64, requests, subprocess

vcm_server = "vcenter.localdomain"
bde_server = "bde.localdomain"
bde_user = "administrator@vsphere.local"
bde_pass = "password"
prefix = "https://"
port = ":8443"

#(vxw-dvs-7-virtualwire-56-sid-5002-5b6c1b81-14b2-434f-9888-54bf1d022a72)
network = "5b6c1b81-14b2-434f-9888-54bf1d022a73"
mob_string = '/mob/?moid=datacenter-2'
curl_cmd = 'curl -k -u ' + bde_user + ':' + bde_pass + ' ' + prefix + vcm_server + mob_string
#grep_cmd = " | grep -oP '(?<=\<\/a\>\s\(vxw).*(?=" + network + "\))'"
grep_cmd = " | grep -oP '(?<=\(vxw).*(?=" + network + "\))' | grep -oE '[^\(]+$'"
awk_cmd = " | awk '{print $0 \"" + network + "\"}'"
#awk_cmd = " | awk '{split($0,uid,\")\"); print \"vxw\" uid[1]}'"
full_cmd = curl_cmd + grep_cmd + awk_cmd

p = subprocess.Popen(full_cmd, stdout=subprocess.PIPE, shell=True)
(network_string, err) = p.communicate()

network_id = network_string.rstrip('\n')
print curl_cmd
print network_id

header = {'content-type': 'application/x-www-form-urlencoded'}
auth_string = "/serengeti/j_spring_security_check"
data = 'j_username=' + bde_user + '&j_password=' + bde_pass
s = requests.session()
url = prefix + bde_server + port + auth_string
r = s.post(url, data, headers=header, verify=False)

header = {'content-type': 'application/json'}
payload = {'name': network, 'portGroup': network_id, 'isDhcp': 'true'}
api_call = '/serengeti/api/networks'
url = prefix + bde_server + port + api_call
r = s.post(url, data=json.dumps(payload), headers=header, verify=False)

print json.dumps(payload)
print
print url
print r.json
print
print r.headers
print r.text
