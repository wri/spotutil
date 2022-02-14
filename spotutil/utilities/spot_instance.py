from __future__ import print_function
from __future__ import absolute_import
from builtins import range
from builtins import object
import os
import sys
import socket
import time

import boto.ec2
import boto3.ec2
from retrying import retry

from . import util

boto_ec2_conn = boto.ec2.connect_to_region('us-east-1')
boto3_ec2_conn = boto3.client('ec2', region_name='us-east-1')


class Instance(object):
    def __init__(self, instance_type, key_pair, price, disk_size, ami_id,
                 flux_model, launch_template, launch_template_version):

        cwd = os.path.dirname(os.path.realpath(__file__))
        self.root_dir = os.path.dirname(cwd)

        self.spot_request = None
        self.instance = None
        self.ssh_ip = None
        self.user = None

        self.instance_type = instance_type
        self.key_pair = key_pair
        self.disk_size = disk_size
        self.price = price
        self.ami_id = ami_id
        self.flux_model = flux_model
        self.launch_template = launch_template
        self.launch_template_version = launch_template_version

        print('Creating a instance type {}'.format(self.instance_type))

    def start(self):
        self.make_request()
        self.wait_for_instance()

    def make_request(self):

        if self.flux_model:
            print('Requesting flux model instance')

            try:
                # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.request_spot_fleet
                self.spot_fleet_request = boto3_ec2_conn.request_spot_fleet(
                    SpotFleetRequestConfig={
                    "IamFleetRole": "arn:aws:iam::838255262149:role/aws-ec2-spot-fleet-tagging-role",
                    "AllocationStrategy": "capacityOptimized",
                    "OnDemandAllocationStrategy": "lowestPrice",
                    "TargetCapacity": 1,
                    "TerminateInstancesWithExpiration": True,
                    "LaunchSpecifications": [],
                    "Type": "request",
                    "LaunchTemplateConfigs": [
                        {
                            "LaunchTemplateSpecification": {
                                "LaunchTemplateId": self.launch_template,
                                # This contains userdata to initialize machine
                                "Version": self.launch_template_version
                            },
                            "Overrides": [
                                {
                                    "InstanceType": self.instance_type,
                                    "WeightedCapacity": 1,
                                    "SubnetId": "subnet-00335589f5f424283"
                                },
                                {
                                    "InstanceType": self.instance_type,
                                    "WeightedCapacity": 1,
                                    "SubnetId": "subnet-8c2b5ea1"
                                },
                                {
                                    "InstanceType": self.instance_type,
                                    "WeightedCapacity": 1,
                                    "SubnetId": "subnet-08458452c1d05713b"
                                },
                                {
                                    "InstanceType": self.instance_type,
                                    "WeightedCapacity": 1,
                                    "SubnetId": "subnet-116d9a4a"
                                },
                                {
                                    "InstanceType": self.instance_type,
                                    "WeightedCapacity": 1,
                                    "SubnetId": "subnet-037b97cff4493e3a1"
                                }
                            ]
                        }
                    ]
                })

                # Because it takes several seconds for an instance to be created in the fleet,
                # the instance information can't be retrieved immediately.
                print("Waiting 15 seconds for flux model spot fleet to be created before obtaining instance ID")
                time.sleep(15)

                # Obtains information on instances in the spot fleet
                # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_spot_fleet_instances
                self.spot_request = boto3_ec2_conn.describe_spot_fleet_instances(
                    SpotFleetRequestId=self.spot_fleet_request["SpotFleetRequestId"]
                )

                # Obtains the SpotInstanceRequestId for the one instance created from the spot fleet request.
                # This is the same variable as created for non-flux model spot instance requests.
                self.spot_active_instances = self.spot_request["ActiveInstances"][0]
                self.request_id = self.spot_request["ActiveInstances"][0]['SpotInstanceRequestId']

                # print("Spot instances full: ", self.spot_request)
                # print("Spot active instance list: ", self.spot_request["ActiveInstances"])
                # print("Spot active instances list dict: ", self.spot_request["ActiveInstances"][0])
                # print("Spot active instances list dict request id: ", self.spot_active_instances['SpotInstanceRequestId'])

            except ClientError as e:
                print("Request failed. Please verify if input parameters are valid")
                print(e.response)
                sys.exit(1)

        else:

            print('Requesting spot instance')

            bdm = self.create_hard_disk()
            ip = self.create_ip()

            config = {'key_name': self.key_pair,
                      'network_interfaces': ip,
                      'dry_run': False,
                      'instance_type': self.instance_type,
                      'block_device_map': bdm,
                      }

            try:
                self.spot_request = boto_ec2_conn.request_spot_instances(self.price, self.ami_id, **config)[0]
            except boto.exception.EC2ResponseError:
                print('Request failed. Please verify if input parameters are valid'.format(self.key_pair))
                sys.exit(1)

        running = False

        while not running:
            time.sleep(5)
            self.spot_request = boto_ec2_conn.get_all_spot_instance_requests(self.spot_request.id)[0]
            state = self.spot_request.state
            print('Spot id {} says: {}'.format(self.spot_request.id, self.spot_request.status.code,
                                               self.spot_request.status.message))

            if state == 'active':
                running = True
                
                # windows
                if os.name == 'nt':
                    self.user = os.getenv('username')
                else:
                    self.user = os.getenv('USER')
                self.spot_request.add_tag('User', self.user)
                self.spot_request.add_tag('Project', "Global Forest Watch")
                self.spot_request.add_tag('Job', "Spotutil")

    @retry(wait_fixed=2000, stop_max_attempt_number=10)
    def wait_for_instance(self):

        print('Instance ID is {}'.format(self.spot_request.instance_id))
        reservations = boto_ec2_conn.get_all_reservations(instance_ids=[self.spot_request.instance_id])
        self.instance = reservations[0].instances[0]

        status = self.instance.update()

        while status == 'pending':
            time.sleep(5)
            status = self.instance.update()
            print('Instance {} is {}'.format(self.instance.id, status))
            
        print('Server IP is {}'.format(self.instance.ip_address))
        print('Private IP is {}'.format(self.instance.private_ip_address))

        if not self.ssh_ip:
            if util.in_office():
                self.ssh_ip = self.instance.ip_address
            else:
                print("Based on your IP, it appears that you're out of the office \n" \
                      "Make sure to connect to the VPN and then ssh/putty using the private IP!")
                self.ssh_ip = self.instance.private_ip_address

        print('Sleeping for 30 seconds to make sure server is ready')
        time.sleep(30)

        instance_tag = 'TEMP-SPOT-{}'.format(self.user)
        self.instance.add_tag("Name", instance_tag)  # change self.tag to TEMP-<usenrmae> SPOT
        self.instance.add_tag("Project", "Global Forest Watch")
        self.instance.add_tag("Pricing", "Spot")
        self.instance.add_tag("Job", "Spotutil")
        self.instance.add_tag("User", self.user)

        self.check_instance_ready()
        
    def create_hard_disk(self):

        dev_sda1 = boto.ec2.blockdevicemapping.EBSBlockDeviceType()
        dev_sda1.size = self.disk_size
        dev_sda1.delete_on_termination = True

        bdm = boto.ec2.blockdevicemapping.BlockDeviceMapping()
        bdm['/dev/sda1'] = dev_sda1

        return bdm

    def create_ip(self):

        subnet_id = 'subnet-116d9a4a'
        security_group_ids = ['sg-3e719042', 'sg-d7a0d8ad', 'sg-6c6a5911']

        interface = boto.ec2.networkinterface.NetworkInterfaceSpecification(subnet_id=subnet_id,
                                                                    groups=security_group_ids,
                                                                    associate_public_ip_address=True)
        interfaces = boto.ec2.networkinterface.NetworkInterfaceCollection(interface)

        return interfaces
        
    def check_instance_ready(self):

        s = socket.socket()
        port = 22  # port number is a number, not string
        for i in range(1, 1000):
            try:
                s.connect((self.ssh_ip, port)) 
                print('Machine is taking ssh connections!')
                break
                
            except Exception as e: 
                print("something's wrong with %s:%d. Exception is %s" % (self.ssh_ip, port, e))
                time.sleep(10)
