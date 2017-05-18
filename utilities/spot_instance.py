import os
import boto.ec2
import time
import subprocess
from retrying import retry

# check if fabric is installed
from fabric.api import env

ec2_conn = boto.ec2.connect_to_region('us-east-1')


class Instance(object):
    def __init__(self, args):

        self.instance_type = args.instance_type
        self.ami_id = args.ami_id
        self.price = args.price
        self.disk_size = args.disk_size
        self.tag = args.tag

        cwd = os.path.dirname(os.path.realpath(__file__))
        self.root_dir = os.path.dirname(cwd)

        self.spot_request = None
        self.instance = None
        self.pem_file = None
        
        print 'Creating a instance type {} from {}'.format(self.instance_type, self.ami_id)

    def start(self):

        self.get_pem()

        self.make_request()

        self.wait_for_instance()
        
    def run(self, local_file_path, proc_type):

        if local_file_path:

            utilities_dir = os.path.join(self.root_dir, 'utilities')
            full_local_path = os.path.realpath(local_file_path)
            print "this is the full local path: {}".format(full_local_path)
            fab_cmd = 'start_process:{},{}'.format(full_local_path, proc_type)

            host_name = 'ubuntu@{0}'.format(self.instance.ip_address)
            print "host address is: {}".format(host_name)

            cmd = ['fab', fab_cmd, '-i', self.pem_file, '-H', host_name]
            subprocess.check_call(cmd, cwd=utilities_dir)

    def get_pem(self):
        self.pem_file = os.path.join(self.root_dir, 'tokens', 'chofmann-wri.pem')
        
        if not os.path.exists(self.pem_file):
            raise ValueError('Could not find token {}'.format(self.pem_file))


    def make_request(self):
        print 'requesting spot instance'

        bdm = self.create_hard_disk()

        config = {'key_name': 'chofmann-wri',
                  'subnet_id': 'subnet-c9679abe',
                  'security_group_ids': ['sg-827f1bfa'],
                  'dry_run': False,
                  'instance_type': self.instance_type,
                  'block_device_map': bdm}

        self.spot_request = ec2_conn.request_spot_instances(self.price, self.ami_id, **config)[0]

        running = False

        while not running:
            time.sleep(5)
            self.spot_request = ec2_conn.get_all_spot_instance_requests(self.spot_request.id)[0]
            state = self.spot_request.state
            print 'Spot id {} says: {}'.format(self.spot_request.id, self.spot_request.status.code,
                                               self.spot_request.status.message)

            if state == 'active':
                running = True

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

        print 'Sleeping for 60 seconds to make sure server is ready'
        time.sleep(60)

        self.instance.add_tag("Name", self.tag)

        
    def create_hard_disk(self):

        dev_sda1 = boto.ec2.blockdevicemapping.EBSBlockDeviceType()
        dev_sda1.size = self.disk_size
        dev_sda1.delete_on_termination = True

        bdm = boto.ec2.blockdevicemapping.BlockDeviceMapping()
        bdm['/dev/sda1'] = dev_sda1

        return bdm
