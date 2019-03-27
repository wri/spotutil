from spotutil.utilities import spot_instance
import os
import sys
import base64


def newspot(instance_type, key_pair, price, disk_size, ami_id, user_data=None):
    """
    Make a spot request for EC2 instance.
    Decode user data to base64 if provided.
    :param instance_type: EC2 istance typ
    :param key_pair: user key name for SSH connection
    :param price: max spot price
    :param disk_size: EBS volume size
    :param ami_id: AMI image ID
    :param user_data: Path to bootstrap script
    """

    if user_data:
        if os.path.isfile(user_data):
            with open(user_data) as f:
                user_data_b64 = base64.b64encode(f.read())
        else:
            print("User data is not a valid file.")
            print("Cannot locate file {}".format(user_data))
            sys.exit(1)
    else:
        user_data_b64 = None

    instance = spot_instance.Instance(
        instance_type, key_pair, price, disk_size, ami_id, user_data_b64
    )

    instance.start()
