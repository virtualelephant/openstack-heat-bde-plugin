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

import logging, json, requests
requests.packages.urllib3.disable_warnings()

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


# Big Data Extensions Endpoint
bde_endpoint = 'bde.localdomain'
username = 'administrator@vsphere.local'
password = 'password'

# Make initial session authenticated session
header = {'content-type': 'application/x-www-form-urlencoded'}
prefix = "https://"
port = ":8443"
auth_string = "/serengeti/j_spring_security_check"
creds = 'j_username=' + username + '&j_password=' + password
url = prefix + bde_endpoint + port + auth_string

s = requests.session()
r = s.post(url, creds, headers=header, verify=False)

#DEBUG
print url
print r.json
#/DEBUG

# Variables that will be passed through Heat
clusterType = "mesos"
clusterName = "mesos_api_01"
clusterState = "stop"

# Setup necessary bits for creating a new cluster
header = {'content-type': 'application/json'}
api_call = '/serengeti/api/cluster/' + clusterName + '?state=' + clusterState
url = prefix + bde_endpoint + port + api_call
r = s.put(url, headers=header, verify=False)

#DEBUG
print
print url
print r.json
print
print r.headers
print r.text
#/DEBUG
