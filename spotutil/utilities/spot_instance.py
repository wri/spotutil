from __future__ import print_function
from __future__ import absolute_import
from builtins import range
from builtins import object
import os
import sys
import socket
import time

import boto3.ec2
from retrying import retry
from botocore.exceptions import ClientError

from . import util

ec2_conn = boto3.client('ec2', region_name='us-east-1')


class Instance(object):
    def __init__(self, instance_type, key_pair, price, disk_size, ami_id,
                 flux_model, launch_template, launch_template_version, use_on_demand):

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

        self.instance_type = instance_type
        self.key_pair = key_pair
        self.disk_size = disk_size
        self.price = price
        self.ami_id = ami_id
        self.flux_model = flux_model
        self.launch_template = launch_template
        self.launch_template_version = launch_template_version
        self.use_on_demand = use_on_demand

        if os.name == 'nt':
            self.user = os.getenv('username')
        else:
            self.user = os.getenv('USER')

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
            # "us-east-1f": "subnet-0360516ee122586ff", # Disables because r5d instances aren't available in it.
        }

        # ec2 instance series (e.g., m4, r4, r5d)
        self.series = self.instance_type.split('.')[0]

        # Assume that if a r5d instance is asked for, a flux model instance should be launched
        if self.series == "r5d":
            self.flux_model = True

        # Theoretically, provides the information to run an on-demand instance. Not tested yet.
        if use_on_demand:
            self.zone = "us-east-1c"
            self.launch_template_version = 30
            print(
                f"Creating on-demand instance type {self.instance_type} in zone {self.zone} using template version {self.launch_template_version}."
            )

        else:
            print("Creating spot instance")
            self._get_best_price()
            print(
                f"Creating a spot instance type {self.instance_type} in zone {self.zone}. Current price: ${self.current_price}"
            )

    def _get_best_price(self):
        """
        Checks for current prices and select subnet in zone with lowest price
        """

        price_history = ec2_conn.describe_spot_price_history(
            InstanceTypes=[self.instance_type],
            MaxResults=len(self.subnet_ids.keys()),
            ProductDescriptions=[self.product_description],
        )

        best_price = None

        # Ignores region us-east-1f for r5d series because that series doesn't work in that region.
        # All other series can consider any region for cheapest region.
        for p in price_history["SpotPriceHistory"]:
            if self.series == "r5d" and p["AvailabilityZone"] == "us-east-1f":
                continue
            if not best_price or float(p["SpotPrice"]) < best_price[1]:
                best_price = (p["AvailabilityZone"], float(p["SpotPrice"]))

        self.zone = best_price[0]
        self.subnet_id = self.subnet_ids[best_price[0]]
        self.current_price = best_price[1]

    def start(self):

        if self.use_on_demand:
            print("On demand branch")
            self.make_on_demand_request()
            print("Made request")
            self.wait_for_spot_instance()
            print("Waiting for request")
        else:
            self.make_spot_request()
            self.wait_for_spot_instance()

    def make_spot_request(self):
        """
        Requests spot instance creation
        """

        # Gets correct configuration for ec2 instance: m4/r4 or r5d (for carbon flux model)
        self._configure_spot_instance()

        # Flux model (r5d instances) and non-flux model instances are created by different routes:
        # fleet request vs. instance request, respectively
        if self.flux_model:
            print('Requesting flux model spot instance')

            try:
                # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.request_spot_fleet
                self.spot_fleet_request = ec2_conn.request_spot_fleet(SpotFleetRequestConfig={**self.config})

            except ClientError as e:
                print("Request failed. Please verify if input parameters are valid")
                print(e.response)
                sys.exit(1)

            # Because it takes several seconds for an instance to be created in the fleet,
            # the instance information can't be retrieved immediately.
            print("Waiting 15 seconds for flux model spot fleet to be created before obtaining instance ID")
            time.sleep(15)

            # Tries several times to get ID. This keeps the process from appearing to fail (no instance ID and IP
            # address returned) but the spot machine is still created.
            for i in range(1, 20):
                try:
                    # Obtains information on instances in the spot fleet
                    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_spot_fleet_instances
                    self.spot_request = ec2_conn.describe_spot_fleet_instances(
                        SpotFleetRequestId=self.spot_fleet_request["SpotFleetRequestId"]
                    )

                    # Obtains the SpotInstanceRequestId for the one instance created from the spot fleet request.
                    # This is the same variable as created for non-flux model spot instance requests.
                    self.spot_active_instances = self.spot_request["ActiveInstances"][0]
                    self.request_id = self.spot_request["ActiveInstances"][0]['SpotInstanceRequestId']

                    continue

                except Exception:
                    print("Cannot acquire flux instance ID yet. Waiting 10 seconds to try again.")
                    time.sleep(10)

        # For non-r5d instances
        else:
            print('Requesting spot instance')

            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.request_spot_instances
            try:
                self.spot_request = ec2_conn.request_spot_instances(**self.config)[
                    "SpotInstanceRequests"
                ][0]
                self.request_id = self.spot_request["SpotInstanceRequestId"]
            except ClientError as e:
                print("Request failed. Please verify if input parameters are valid")
                print(e.response)
                sys.exit(1)

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

    def make_on_demand_request(self):
        """
        Requests on-demand instance creation
        """

        # Gets correct configuration for ec2 instance: m4/r4 or r5d (for carbon flux model)
        self._configure_on_demand_instance()

        # Flux model (r5d instances) and non-flux model instances are created by different routes:
        # fleet request vs. instance request, respectively
        if self.flux_model:
            print('Requesting flux model spot instance')

            try:
                # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.request_spot_fleet
                self.on_demand_request = ec2_conn.request_spot_fleet(SpotFleetRequestConfig={**self.config})

            except ClientError as e:
                print("Request failed. Please verify if input parameters are valid")
                print(e.response)
                sys.exit(1)

            # Because it takes several seconds for an instance to be created in the fleet,
            # the instance information can't be retrieved immediately.
            print("Waiting 15 seconds for flux model spot fleet to be created before obtaining instance ID")
            time.sleep(15)

            # Tries several times to get ID. This keeps the process from appearing to fail (no instance ID and IP
            # address returned) but the spot machine is still created.
            for i in range(1, 20):
                try:
                    # Obtains information on instances in the spot fleet
                    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_spot_fleet_instances
                    self.spot_request = ec2_conn.describe_spot_fleet_instances(
                        SpotFleetRequestId=self.spot_fleet_request["SpotFleetRequestId"]
                    )

                    # Obtains the SpotInstanceRequestId for the one instance created from the spot fleet request.
                    # This is the same variable as created for non-flux model spot instance requests.
                    self.spot_active_instances = self.spot_request["ActiveInstances"][0]
                    self.request_id = self.spot_request["ActiveInstances"][0]['SpotInstanceRequestId']

                    continue

                except Exception:
                    print("Cannot acquire flux instance ID yet. Waiting 10 seconds to try again.")
                    time.sleep(10)

        # For non-r5d instances
        else:
            print('Requesting spot instance')

            # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.request_spot_instances
            try:
                self.spot_request = ec2_conn.request_spot_instances(**self.config)[
                    "SpotInstanceRequests"
                ][0]
                self.request_id = self.spot_request["SpotInstanceRequestId"]
            except ClientError as e:
                print("Request failed. Please verify if input parameters are valid")
                print(e.response)
                sys.exit(1)

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

    def _configure_spot_instance(self):
        """
        Configures instance request
        """

        # Configuration for flux model spot fleet is different from configuration for other spot instances
        if self.flux_model == True:
            print(f"Creating spot machine from flux model config and launch template version {self.launch_template_version}")

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
                            "LaunchTemplateId": self.launch_template,  # This contains userdata to initialize machine
                            "Version": self.launch_template_version
                        },
                        # r5d instances do not work in region us-east-1f, so not provided as a possibility
                        "Overrides": [
                            {
                                "InstanceType": self.instance_type,
                                "WeightedCapacity": 1,
                                "SubnetId": list(self.subnet_ids.values())[0]
                            },
                            {
                                "InstanceType": self.instance_type,
                                "WeightedCapacity": 1,
                                "SubnetId": list(self.subnet_ids.values())[1]
                            },
                            {
                                "InstanceType": self.instance_type,
                                "WeightedCapacity": 1,
                                "SubnetId": list(self.subnet_ids.values())[2]
                            },
                            {
                                "InstanceType": self.instance_type,
                                "WeightedCapacity": 1,
                                "SubnetId": list(self.subnet_ids.values())[3]
                            },
                            {
                                "InstanceType": self.instance_type,
                                "WeightedCapacity": 1,
                                "SubnetId": list(self.subnet_ids.values())[4]
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
                    # Flux model spot machines mount SSD drives. Other series of machines use an EBS volume.
                    "BlockDeviceMappings": [
                        {
                            "DeviceName": "/dev/sda1",
                            "Ebs": {
                                "DeleteOnTermination": True,
                                "VolumeSize": self.disk_size,
                                "VolumeType": self.volume_type,
                                "Encrypted": False,
                            },
                        }
                    ]
                },
            }

    def _configure_on_demand_instance(self):
        """
        Configures instance request
        """

        # Configuration for flux model spot fleet is different from configuration for other spot instances
        if self.flux_model == True:
            print(
                f"Creating on-demand machine from flux model config and launch template version {self.launch_template_version}")

            self.config = {
                  "MaxCount": 1,
                  "MinCount": 1,
                  "ImageId": "ami-08f3d892de259504d",
                  "InstanceType": "r5d.24xlarge",
                  "SubnetId": "subnet-08458452c1d05713b",
                  "KeyName": "r5d_ec2",
                  "EbsOptimized": false,
                  "UserData": "IyEvYmluL2Jhc2gKeXVtIGluc3RhbGwgLXkgcnN5bmMgZ2l0IG5hbm8gaHRvcCB0bXV4CgojIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMKIyBNb3VudCB0aGUgZXBoZW1lcmFsIFNTRCBzdG9yYWdlLgojIElmIGZvdXIgdm9sdW1lcyBleGlzdCwgbWVyZ2UgdGhlbSBhbmQgbW91bnQgam9pbnRseS4KIyBJZiBvbmx5IHR3byB2b2x1bWVzIGV4aXN0LCBtZXJnZSB0aGVtIGFuZCBtb3VudCBqb2ludGx5LgojIElmIG9ubHkgb25lIHZvbHVtZSBleGlzdHMsIGp1c3QgbW91bnQgdGhhdC4gCiMgUmVnYXJkbGVzcyBvZiBob3cgbWFueSB2b2x1bWVzIHRoZXJlIGFyZSwgdGhlIG5hbWUgb2YgdGhlIGZvbGRlciB0aGV5IGFyZSBtb3VudGVkIHRvIGlzIHRoZSBzYW1lLiAKIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjCiMgTmFtZSBvZiB0aGUgc2Vjb25kIHZvbHVtZSAoaWYgaXQgZXhpc3RzKQpTU0QyPW52bWUybjEKCiMgTmFtZSBvZiB0aGUgZm91cnRoIHZvbHVtZSAoaWYgaXQgZXhpc3RzKQpTU0Q0PW52bWU0bjEKCiMgQ2hlY2tzIGlmIHRoZSBzZWNvbmQgdm9sdW1lIGV4aXN0cwpDSEVDSzI9JChsc2JsayAtbCB8IGdyZXAgJFNTRDIpCgojIENoZWNrcyBpZiB0aGUgZm91cnRoIHZvbHVtZSBleGlzdHMKQ0hFQ0s0PSQobHNibGsgLWwgfCBncmVwICRTU0Q0KQoKIyBDaGVja3MgZm9yIGZvdXIgdm9sdW1lcyBmaXJzdCwgdGhlbiBmb3IgdHdvIHZvbHVtZXMKaWYgW1sgJENIRUNLNCBdXQp0aGVuCiAgIyBGb3VydGggU1NEIHZvbHVtZSBmb3VuZAogICMgRm9sbG93cyBodHRwczovL29iamVjdGl2ZWZzLmNvbS9ob3d0by9ob3ctdG8tcmFpZC1lYzItaW5zdGFuY2Utc3RvcmVzCiAgc3VkbyBtZGFkbSAtLWNyZWF0ZSAtLXZlcmJvc2UgL2Rldi9tZDAgLS1sZXZlbD0wIC0tbmFtZT1NWV9SQUlEIC0tY2h1bms9NjQgLS1yYWlkLWRldmljZXM9NCAvZGV2L252bWUxbjEgL2Rldi9udm1lMm4xIC9kZXYvbnZtZTNuMSAvZGV2L252bWU0bjEgICNyZXF1aXJlcyBzdXBlcnVzZXIgc3RhdHVzIHRvIHVzZSBzdWRvLCBhbmQgZG9lc24ndCB3b3JrIHdpdGhvdXQgc3VkbwogIHN1ZG8gbWtmcy5leHQ0IC1MIE1ZX1JBSUQgL2Rldi9tZDAgICNyZXF1aXJlcyBzdWRvIHRvIGRldGVybWluZSBmaWxlIHN5c3RlbSBzaXplCiAgc3VkbyBta2RpciAtcCAvbW50L2V4dCAgIyBkb2VzbuKAmXQgbmVlZCBzdWRvIGJ1dCBhZGRpbmcgZm9yIGNvbnNpc3RlbmN5CiAgc3VkbyBtb3VudCAtdCBleHQ0IC9kZXYvbWQwIC9tbnQvZXh0ICAjIG5lZWRzIHN1ZG8gYmVjYXVzZSBvbmx5IHJvb3QgY2FuIHVzZSAtLXR5cGVzIG9wdGlvbgoKZWxpZiBbWyAkQ0hFQ0syIF1dCnRoZW4KICAjIFNlY29uZCBTU0Qgdm9sdW1lIGZvdW5kCiAgIyBGb2xsb3dzIGh0dHBzOi8vb2JqZWN0aXZlZnMuY29tL2hvd3RvL2hvdy10by1yYWlkLWVjMi1pbnN0YW5jZS1zdG9yZXMKICBzdWRvIG1kYWRtIC0tY3JlYXRlIC0tdmVyYm9zZSAvZGV2L21kMCAtLWxldmVsPTAgLS1uYW1lPU1ZX1JBSUQgLS1jaHVuaz02NCAtLXJhaWQtZGV2aWNlcz0yIC9kZXYvbnZtZTFuMSAvZGV2L252bWUybjEgICAjcmVxdWlyZXMgc3VwZXJ1c2VyIHN0YXR1cyB0byB1c2Ugc3VkbywgYW5kIGRvZXNuJ3Qgd29yayB3aXRob3V0IHN1ZG8KICBzdWRvIG1rZnMuZXh0NCAtTCBNWV9SQUlEIC9kZXYvbWQwICAjcmVxdWlyZXMgc3VkbyB0byBkZXRlcm1pbmUgZmlsZSBzeXN0ZW0gc2l6ZQogIHN1ZG8gbWtkaXIgLXAgL21udC9leHQgICMgZG9lc27igJl0IG5lZWQgc3VkbyBidXQgYWRkaW5nIGZvciBjb25zaXN0ZW5jeQogIHN1ZG8gbW91bnQgLXQgZXh0NCAvZGV2L21kMCAvbW50L2V4dCAgIyBuZWVkcyBzdWRvIGJlY2F1c2Ugb25seSByb290IGNhbiB1c2UgLS10eXBlcyBvcHRpb24KCmVsc2UKICAjIE9ubHkgb25lIFNTRCB2b2x1bWUKICBta2ZzLmV4dDQgL2Rldi9udm1lMW4xCiAgbWtkaXIgLXAgL21udC9leHQKICBtb3VudCAtdCBleHQ0IC9kZXYvbnZtZTFuMSAvbW50L2V4dApmaQoKCiMgbWFrZSB0ZW1wIGRpcmVjdG9yeSBmb3IgY29udGFpbmVycyB1c2FnZQojIHNob3VsZCBiZSB1c2VkIGluIHRoZSBCYXRjaCBqb2IgZGVmaW5pdGlvbiAoTW91bnRQb2ludHMpCm1rZGlyIC9tbnQvZXh0L3RtcApyc3luYyAtYXZQSFNYIC90bXAvIC9tbnQvZXh0L3RtcC8gCgpta2RpciAtcCAvdmFyL2xpYi9kb2NrZXIKbWtkaXIgLXAgL21udC9leHQvZG9ja2VyCgojIG1vZGlmeSBmc3RhYiB0byBtb3VudCAvdG1wIG9uIHRoZSBuZXcgc3RvcmFnZS4Kc2VkIC1pICckIGEgL21udC9leHQvdG1wICAvdG1wICBub25lICBiaW5kICAwIDAnIC9ldGMvZnN0YWIKc2VkIC1pICckIGEgL21udC9leHQvZG9ja2VyIC92YXIvbGliL2RvY2tlciBub25lICBiaW5kICAwIDAnIC9ldGMvZnN0YWIKbW91bnQgLWEKCiMgbWFrZSAvdG1wIHVzYWJsZSBieSBldmVyeW9uZQpjaG1vZCA3NzcgL21udC9leHQvdG1wCgojIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMKIyBJbnN0YWxsIGRvY2tlciBhbmQgZG9ja2VyLWNvbXBvc2UsIHBlciBodHRwczovL2FjbG91ZHhwZXJ0LmNvbS9ob3ctdG8taW5zdGFsbC1kb2NrZXItY29tcG9zZS1vbi1hbWF6b24tbGludXgtYW1pLwojIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMKCnl1bSBpbnN0YWxsIC15IGRvY2tlcgoKY3VybCAtTCBodHRwczovL2dpdGh1Yi5jb20vZG9ja2VyL2NvbXBvc2UvcmVsZWFzZXMvZG93bmxvYWQvMS4yNS40L2RvY2tlci1jb21wb3NlLWB1bmFtZSAtc2AtYHVuYW1lIC1tYCB8IHN1ZG8gdGVlIC91c3IvbG9jYWwvYmluL2RvY2tlci1jb21wb3NlID4gL2Rldi9udWxsCmNobW9kICt4IC91c3IvbG9jYWwvYmluL2RvY2tlci1jb21wb3NlCmxuIC1zIC91c3IvbG9jYWwvYmluL2RvY2tlci1jb21wb3NlIC91c3IvYmluL2RvY2tlci1jb21wb3NlCmRvY2tlci1jb21wb3NlIC0tdmVyc2lvbgoKIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMKIyBDbG9uZSBsYXRlc3QgZmx1eCBtb2RlbCByZXBvIHRvIHRoZSBob21lIGZvbGRlcgojIGNsb25lIGNvbW1hbmQgc3VnZ2VzdGVkIGJ5IExvZ2FuIEJ5ZXJzLiBJdCByZXNvbHZlcyB0aGUgcHJvYmxlbSBvZiBub3QgYmVpbmcgYWJsZSB0byBwdWxsIHRoZSByZXBvIGFmdGVyIGl0IHdhcyBjbG9uZWQsIHdoaWNoIHdhcyBjb25mbGljdGluZyB3aXRoIG5vdCBiZWluZyBhYmxlIHRvIFNTSCBpbnRvIHRoZSBtYWNoaW5lIG1vcmUgdGhhbiB+MSBtaW51dGUgYWZ0ZXIgaXQgd2FzIGNyZWF0ZWQuCiMgVGhpcyBmb3JtdWxhdGlvbiBvZiBnaXQgY2xvbmUgbWFrZXMgZWMyLXVzZXIgdGhlIGNsb25lciwgcmF0aGVyIHRoYW4gcm9vdC4gSXQncyBubyBsb25nZXIgbmVjZXNzYXJ5IHRvIGNoYW5nZSBvd25lcnNoaXAgKGNob3duKSBvZiB0aGUgcmVwbyBiZWNhdXNlIGNhcmJvbi1idWRnZXQgd2lsbCBhbHJlYWR5IGJlIG93bmVkIGJ5IGVjMi11c2VyLCBub3Qgcm9vdC4KIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMKY2QgL2hvbWUvZWMyLXVzZXIKc3UgZWMyLXVzZXIgLWMgImdpdCBjbG9uZSBodHRwczovL2dpdGh1Yi5jb20vd3JpL2NhcmJvbi1idWRnZXQiCgojIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMKIyBTdGFydHMgdGhlIGRvY2tlciBzZXJ2aWNlCiMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIwpzdWRvIHNlcnZpY2UgZG9ja2VyIHN0YXJ0CgojIFJlcGxhY2VzIGh0b3AgY29uZmlnIGZpbGUgd2l0aCBteSBwcmVmZXJyZWQgY29uZmlndXJhdGlvbgpta2RpciAtcCAvaG9tZS9lYzItdXNlci8uY29uZmlnL2h0b3AvCmNwIC9ob21lL2VjMi11c2VyL2NhcmJvbi1idWRnZXQvaHRvcHJjIC9ob21lL2VjMi11c2VyLy5jb25maWcvaHRvcC9odG9wcmM=",
                  "LaunchTemplate": {
                    "LaunchTemplateId": "lt-00205de607ab6d4d9",
                    "Version": "30"
                  },
                  "SecurityGroupIds": [
                    "sg-3e719042",
                    "sg-d7a0d8ad",
                    "sg-6c6a5911"
                  ]
                }

        else:
            print("Not flux model")

    def _update_request_state(self):
        """
        Check state of request and update self.state
        """

        time.sleep(5)

        # Obtain spot request state
        self.spot_request = ec2_conn.describe_spot_instance_requests(
            SpotInstanceRequestIds=[self.request_id]
        )["SpotInstanceRequests"][0]
        self.state = self.spot_request["State"]

        print(
            "Spot request {}. Status: {} -- {}".format(
                self.spot_request["State"],
                self.spot_request["Status"]["Code"],
                self.spot_request["Status"]["Message"],
            )
        )

    @retry(wait_fixed=2000, stop_max_attempt_number=10)
    def wait_for_spot_instance(self):

        print("Instance ID is {}".format(self.spot_request["InstanceId"]))

        ec2 = boto3.resource("ec2")
        self.instance = ec2.Instance(self.spot_request["InstanceId"])
        self._tag_instance()

        while self.instance.state == "pending":
            time.sleep(5)
            self.instance.reload()
            print("Instance {} is {}".format(self.instance.id, self.instance.state))

        self._instance_ips()

        print('Sleeping for 30 seconds to make sure server is ready')
        time.sleep(30)

        self.check_instance_ready()

    def check_instance_ready(self):
        """
        Tests SSH connection to spot machine
        """

        s = socket.socket()
        port = 22  # port number is a number, not string
        for i in range(1, 1000):
            try:
                s.connect((self.ssh_ip, port))
                print('Machine is taking ssh connections!')
                break

            except Exception as e:
                print("Something's wrong with %s:%d. Exception is %s" % (self.ssh_ip, port, e))
                time.sleep(10)

    def _tag_request(self):
        """
        Adds tags to instance for internal accounting
        """

        tags = [
            {"Key": "User", "Value": self.user},
            {"Key": "Project", "Value": self.project},
            {"Key": "Job", "Value": self.job},
        ]
        ec2_conn.create_tags(Resources=[self.request_id], Tags=tags)

    def _tag_instance(self):
        """
        Adds tags to instance for internal accounting
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
        Prints out instance public and private IP
        Sets SSH IP based on user location (in WRI DC office or not)
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