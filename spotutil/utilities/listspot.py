from __future__ import print_function
from __future__ import absolute_import
import boto3
from prettytable import PrettyTable
from spotutil.utilities.util import launchtime


def listspot():

    ec2_conn = boto3.client("ec2", region_name="us-east-1")
    filters = {"Filters": [{"Name": "state", "Values": ["active"]}]}
    spot_request = ec2_conn.describe_spot_instance_requests(**filters)

    table_columns = ["User", "Instance Type", "Internal IP", "External IP", "Up Time"]
    table = PrettyTable(table_columns)

    for c in table_columns:
        table.align[c] = "l"

    spot_info_list = []

    if spot_request:
        for r in spot_request["SpotInstanceRequests"]:
            spot_dict = {}
            instance_id = r["InstanceId"]
            request_id = r["SpotInstanceRequestId"]

            ec2 = boto3.resource("ec2")
            instance = ec2.Instance(instance_id)

            launch_info = launchtime(instance.launch_time)
            instance_type = instance.instance_type
            internal_ip = instance.private_ip_address
            external_ip = instance.public_ip_address
            tags = instance.tags

            try:
                user = [t["Value"] for t in tags if t["Key"] == "User"][0]
            except (KeyError, IndexError, TypeError):
                user = "Unknown"

            table.add_row([user, instance_type, internal_ip, external_ip, launch_info])

            spot_dict["instance_id"] = instance_id
            spot_dict["internal_ip"] = internal_ip
            spot_dict["external_ip"] = external_ip
            spot_dict["user"] = user
            spot_dict["id"] = request_id
            spot_info_list.append(spot_dict)

        print(table)
        return table, spot_info_list

    else:
        print("No active Spot requests found.")
