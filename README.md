# Virtual Elephant OpenStack Heat Resource Plugin
# for VMware Big Data Extensions

An OpenStack Heat resource plugin for integrating VMware Big Data Extensions. Allows dynamic deployment of Hadoop, Apache Mesos, Apache Spark, Apache Cassandra, Apache Kafka and other cluster deployments into an OpenStack environment using OpenStack Heat templates (JSON or YAML). Allows for the private cloud architect to offer Platform-as-a-Service offerings within their OpenStack environment using the OpenStack REST API to their end-users.

# Installation Guide

In order to begin using the resource plugin, the VMware Big Data Extensions management server will need to be modified. Depending on how many of the additional cluster deployments you have integrated from the Virtual Elephant site, additional steps may be required to enable deployments of every cluster type. The resource plugin, REST API test scripts and the updated JAVA files can be downloaded from the Virtual Elephant GitHub site. Once you have checked-out the repository, perform the following steps to within your environment.

Note: I am using VMware Integrated OpenStack and the paths reflect that environment. You may need to adjust the commands for your implementation.

Copy the resource plugin (BigDataExtensions.py) to OpenStack controller(s):

$ scp plugin/BigDataExtensions.py user@controller1.localdomain:/usr/lib/heat
$ ssh user@controller1.localdomain "service heat-engine restart"
$ ssh user@controller1.localdomain "grep VirtualElephant /var/log/heat/heat-engine.log"
$ scp plugin/BigDataExtensions.py user@controller2.localdomain:/usr/lib/heat
$ ssh user@controller2.localdomain "service heat-engine restart"
$ ssh user@controller2.localdomain "grep VirtualElephant /var/log/heat/heat-engine.log"

Copy the update JAVA files to the Big Data Extensions management server:

$ scp java/cluster-mgmt-2.1.1.jar user@bde.localdomain:/opt/serengeti/tomcat6/webapps/serengeti/WEB-INF/lib/
$ scp java/commons-serengeti-2.1.1.jar user@bde.localdomain:/opt/serengeti/tomcat6/webapps/serengeti/WEB-INF/lib/
$ scp java/commons-serengeti-2.1.1.jar user@bde.localdomain:/opt/serengeti/cli/conf/
$ ssh user@bde.localdomain "service tomcat restart"

If using VMware Integrated OpenStack, the curl package is required:

$ ssh user@controller1.localdomain "apt-get -y install curl"
$ ssh user@controller2.localdomain "apt-get -y install curl"

At this point, the OpenStack controller(s) where Heat is running now have the resource plugin installed and you should have seen an entry stating it was registered when you restarted the heat-engine service. In addition, the management server for Big Data Extensions have the required updates that will allow the REST API to support the resource plugin. The next steps before the plugin can be consumed, will be to copy/create JSON files for the cluster-types you intend to support within the environment. Within the GitHub repository, you will have found several example JSON files that can be used. One of the updates to the management server included logic to look in the /opt/serengeti/conf file for these JSON files.

Copy example mesos-default-template-spec.json file:
$ scp json/mesos-default-template-spec.json user@bde.localdomain:/opt/serengeti/conf/
