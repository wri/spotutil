from __future__ import print_function
from __future__ import absolute_import
from builtins import range
from builtins import object
from botocore.exceptions import ClientError
from . import util

# from retrying import retry
import os
import sys
import socket
import time
import boto3

ec2_conn = boto3.client("ec2", region_name="us-east-1")


class Instance(object):
    def __init__(self, instance_type, key_pair, price, disk_size, ami_id,
                 flux_model, launch_template, launch_template_version):

        cwd = os.path.dirname(os.path.realpath(__file__))
        self.root_dir = os.path.dirname(cwd)

        self.spot_request = None
        self.instance = None
        self.ssh_ip = None
        self.user = None
        self.subnet_id = None
        self.current_price = None
        self.zone = None
        self.request_id = None
        self.state = None

        self.config = dict()

        self.instance_type = instance_type
        self.key_pair = key_pair
        self.disk_size = disk_size
        self.price = price
        self.ami_id = ami_id
        self.flux_model = flux_model
        self.launch_template = launch_template
        self.launch_template_version = launch_template_version

        # windows
        if os.name == "nt":
            self.user = os.getenv("username")
        else:
            self.user = os.getenv("USER")

        self.project = "Global Forest Watch"
        self.job = "Spotutil"
        self.product_description = "Linux/UNIX (Amazon VPC)"
        self.volume_type = "gp2"
        self.request_type = "one-time"
        self.security_group_ids = ["sg-3e719042", "sg-d7a0d8ad", "sg-6c6a5911"]
        self.subnet_ids = {
            "us-east-1a": "subnet-00335589f5f424283",
            "us-east-1b": "subnet-8c2b5ea1",
            "us-east-1c": "subnet-08458452c1d05713b",
            "us-east-1d": "subnet-116d9a4a",
            "us-east-1e": "subnet-037b97cff4493e3a1",
            "us-east-1f": "subnet-037b97cff4493e3a1",
        }

        self._get_best_price()

        print(
            "Creating an instance type {} in zone {}. Current price: ${}".format(
                self.instance_type, self.zone, self.current_price
            )
        )

    def start(self):
        self._make_request()
        self._wait_for_instance()

    def _make_request(self):
        """
        Request a spot instance. Make sure that requests doesn't fail.
        If it does fail, exit.
        """

        print("Requesting spot instance")
        self._configure_instance()

        # Carbon flux model requires a spot fleet be launched (with 1 instance) using a launch template
        # created in the AWS ec2 console.
        if self.flux_model:

            print("Creating flux model spot fleet")

            try:
                # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.request_spot_fleet
                self.spot_fleet_request = ec2_conn.request_spot_fleet(SpotFleetRequestConfig={**self.config})

                # Because it takes several seconds for an instance to be created in the fleet,
                # the instance information can't be retrieved immediately.
                print("Waiting 15 seconds for flux model spot fleet to be created before obtaining instance ID")
                time.sleep(15)

                # Obtains information on instances in the spot fleet
                # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_spot_fleet_instances
                self.spot_request = ec2_conn.describe_spot_fleet_instances(
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

        # For non-flux model spot requests-- no spot fleet created, just a single instance
        else:

            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.request_spot_instances
            try:
                self.spot_request = ec2_conn.request_spot_instances(**self.config)[
                    "SpotInstanceRequests"
                ][0]
            except ClientError as e:
                print("Request failed. Please verify if input parameters are valid")
                print(e.response)
                sys.exit(1)

            # print(self.spot_request)
            # print(self.spot_request["SpotInstanceRequestId"])

            print("Waiting 15 seconds for request to be created before obtaining instance ID")
            time.sleep(15)

            self.request_id = self.spot_request["SpotInstanceRequestId"]

        running = False
        while not running:

            self._update_request_state()

            if self.state == "active":
                running = True
                self._tag_request()

            elif self.state == "failed":
                print(
                    "{} - {}".format(
                        self.spot_request["Fault"]["Code"],
                        self.spot_request["Fault"]["Message"],
                    )
                )
                sys.exit(1)

    # @retry(wait_fixed=2000, stop_max_attempt_number=10)
    def _wait_for_instance(self):
        """
        Add tags to instance for accounting.
        Wait for instance to boot and make sure user can connect to it via SSH.
        """

        print("Instance ID is {}".format(self.spot_request["InstanceId"]))

        ec2 = boto3.resource("ec2")
        self.instance = ec2.Instance(self.spot_request["InstanceId"])
        self._tag_instance()

        while self.instance.state == "pending":
            time.sleep(5)
            self.instance.reload()
            print("Instance {} is {}".format(self.instance.id, self.instance.state))

        self._instance_ips()

        print("Sleeping for 30 seconds to make sure server is ready")
        time.sleep(30)

        self._check_instance_ready()

    def _update_request_state(self):
        """
        Check state of request and update self.state
        """
        time.sleep(5)
        self.spot_request = ec2_conn.describe_spot_instance_requests(
            SpotInstanceRequestIds=[self.request_id]
        )["SpotInstanceRequests"][0]
        self.state = self.spot_request["State"]
        print(
            "Spot request {}. Status: {} - {}".format(
                self.spot_request["State"],
                self.spot_request["Status"]["Code"],
                self.spot_request["Status"]["Message"],
            )
        )

    def _tag_request(self):
        """
        Add tags to spot request
        """

        tags = [
            {"Key": "User", "Value": self.user},
            {"Key": "Project", "Value": self.project},
            {"Key": "Job", "Value": self.job},
        ]
        ec2_conn.create_tags(Resources=[self.request_id], Tags=tags)

    def _tag_instance(self):
        """
        Add tags to instance for internal accounting
        """
        tags = [
            {"Key": "User", "Value": self.user},
            {"Key": "Project", "Value": self.project},
            {"Key": "Job", "Value": self.job},
            {"Key": "Pricing", "Value": "Spot"},
        ]
        self.instance.create_tags(DryRun=False, Tags=tags)

    def _instance_ips(self):
        """
        Print out instance public and private IP
        Set SSH IP based on user location (In WRI office or not)
        """
        print("Server IP is {}".format(self.instance.public_ip_address))
        print("Private IP is {}".format(self.instance.private_ip_address))

        if not self.ssh_ip:
            if util.in_office():
                self.ssh_ip = self.instance.public_ip_address
            else:
                print(
                    "Based on your IP, it appears that you're out of the office \n"
                    "Make sure to connect to the VPN and then ssh/putty using the private IP!"
                )
                self.ssh_ip = self.instance.private_ip_address

    def _check_instance_ready(self):
        """
        Try to SSH into instance to make sure machine is up and accepts connections
        """

        s = socket.socket()
        port = 22  # port number is a number, not string
        for i in range(1, 1000):
            try:
                s.connect((self.ssh_ip, port))
                print("Machine is taking ssh connections!")
                break

            except Exception as e:
                print(
                    "Something's wrong with %s:%d. Exception is: %s"
                    % (self.ssh_ip, port, e)
                )
                time.sleep(10)

    def _get_best_price(self):
        """
        Check for current prices and select subnet in zone with lowest price
        """

        # ec2 instance series (e.g., m4, r5d)
        series = self.instance_type.split('.')[0]

        price_history = ec2_conn.describe_spot_price_history(
            InstanceTypes=[self.instance_type],
            MaxResults=len(self.subnet_ids.keys()),
            ProductDescriptions=[self.product_description],
        )

        best_price = None

        # Ignores region us-east-1f for r5d series because that series doesn't work in that region.
        # All other series can consider any region for cheapest region.
        for p in price_history["SpotPriceHistory"]:
            if series == "r5d" and p["AvailabilityZone"] == "us-east-1f":
                continue
            if not best_price or float(p["SpotPrice"]) < best_price[1]:
                best_price = (p["AvailabilityZone"], float(p["SpotPrice"]))

        self.zone = best_price[0]
        self.subnet_id = self.subnet_ids[best_price[0]]
        self.current_price = best_price[1]

    def _configure_instance(self):
        """
        Configure instance request
        """

        # Configuration for flux model spot fleet is different from configuration for other spot instances
        if self.flux_model == True:
            print("Creating spot machine from flux model config and launch template")

            self.config = {
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
            }

        else:
            self.config = {
                "Type": self.request_type,
                "DryRun": False,
                "LaunchSpecification": {
                    "ImageId": self.ami_id,
                    "KeyName": self.key_pair,
                    "InstanceType": self.instance_type,
                    "NetworkInterfaces": [
                        {
                            "AssociatePublicIpAddress": True,
                            "DeviceIndex": 0,
                            "SubnetId": self.subnet_id,
                            "Groups": self.security_group_ids,
                        }
                    ],
                },
            }

        if self.price:
            self.config["SpotPrice"] = str(self.price)

        if self.disk_size and not self.flux_model:
            self.config["LaunchSpecification"]["BlockDeviceMappings"] = [
                {
                    "DeviceName": "/dev/sdf",
                    "Ebs": {
                        "DeleteOnTermination": True,
                        "VolumeSize": self.disk_size,
                        "VolumeType": self.volume_type,
                        "Encrypted": False,
                    },
                }
            ]
