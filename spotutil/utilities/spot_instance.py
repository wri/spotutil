import os
import sys
import socket
import time

import boto.ec2
from retrying import retry

import util

ec2_conn = boto.ec2.connect_to_region('us-east-1')


class Instance(object):
    def __init__(self, instance_type, key_pair, price, disk_size, ami_id):

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

        print 'Creating a instance type {}'.format(self.instance_type)

    def start(self):

        self.make_request()

        self.wait_for_instance()

    def make_request(self):
        print 'requesting spot instance'

        bdm = self.create_hard_disk()
        ip = self.create_ip()

        config = {'key_name': self.key_pair,
                  'network_interfaces': ip,
                  'dry_run': False,
                  'instance_type': self.instance_type,
                  'block_device_map': bdm}

        try:
            self.spot_request = ec2_conn.request_spot_instances(self.price, self.ami_id, **config)[0]
        except boto.exception.EC2ResponseError:
            print 'Key pair {} is not registered with AWS. Please double check the key pair passed, ' \
                             'and if necessary create a new key'.format(self.key_pair)
            sys.exit(1)

        running = False

        while not running:
            time.sleep(5)
            self.spot_request = ec2_conn.get_all_spot_instance_requests(self.spot_request.id)[0]
            state = self.spot_request.state
            print 'Spot id {} says: {}'.format(self.spot_request.id, self.spot_request.status.code,
                                               self.spot_request.status.message)

            if state == 'active':
                running = True
                
                # windows
                if os.name == 'nt':
                    self.user = os.getenv('username')
                else:
                    self.user = os.getenv('USER')
                self.spot_request.add_tag('User', self.user)

    @retry(wait_fixed=2000, stop_max_attempt_number=10)
    def wait_for_instance(self):

        print 'Instance ID is {}'.format(self.spot_request.instance_id)
        reservations = ec2_conn.get_all_reservations(instance_ids=[self.spot_request.instance_id])
        self.instance = reservations[0].instances[0]

        status = self.instance.update()

        while status == 'pending':
            time.sleep(5)
            status = self.instance.update()
            print 'Instance {} is {}'.format(self.instance.id, status)
            
        print 'Server IP is {}'.format(self.instance.ip_address)
        print 'Private IP is {}'.format(self.instance.private_ip_address)

        if not self.ssh_ip:
            if util.in_office():
                self.ssh_ip = self.instance.ip_address
            else:
                print "Based on your IP, it appears that you're out of the office \n" \
                      "Make sure to connect to the VPN and then ssh/putty using the private IP!"
                self.ssh_ip = self.instance.private_ip_address

        print 'Sleeping for 30 seconds to make sure server is ready'
        time.sleep(30)

        instance_tag = 'TEMP-SPOT-{}'.format(self.user)
        self.instance.add_tag("Name", instance_tag)  # change self.tag to TEMP-<usenrmae> SPOT
        
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
                print 'Machine is taking ssh connections!'
                break
                
            except Exception as e: 
                print("something's wrong with %s:%d. Exception is %s" % (self.ssh_ip, port, e))
                time.sleep(10)
