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

bde_server = "bde.localdomain"
bde_user = "administrator@vsphere.local"
bde_pass = "password"
prefix = "https://"
port = ":8443"

network = "6cb975a6-ea02-45bc-8429-84d185c429e5"

header = {'content-type': 'application/x-www-form-urlencoded'}
auth_string = "/serengeti/j_spring_security_check"
data = 'j_username=' + bde_user + '&j_password=' + bde_pass
s = requests.session()
url = prefix + bde_server + port + auth_string
r = s.post(url, data, headers=header, verify=False)

header = {'content-type': 'application/json'}
api_call = '/serengeti/api/network/' + network
url = prefix + bde_server + port + api_call
r = s.get(url, headers=header, verify=False)

print
print r.json
print
print r.headers
print r.text
