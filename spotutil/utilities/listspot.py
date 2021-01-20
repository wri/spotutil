from __future__ import print_function
from __future__ import absolute_import
import boto3
from prettytable import PrettyTable
from spotutil.utilities.util import launchtime


def listspot():
    """
    List running instances in a table
    :return: Table , List of running instances
    """
    spot_instances = _get_running_instances()

    ec2_conn = boto.ec2.connect_to_region('us-east-1')
    spot_request = ec2_conn.get_all_spot_instance_requests()

    client = boto3.client('ec2', 'us-east-1')
    table_columns = ['User', 'Instance Type', 'Internal IP', 'External IP', 'Up Time']
    table = PrettyTable(table_columns)
    for c in table_columns:
        table.align[c] = "l"

    if len(spot_instances):
        for spot in spot_instances:
            table.add_row(
                [
                    spot["user"],
                    spot["instance_type"],
                    spot["internal_ip"],
                    spot["external_ip"],
                    spot["launch_info"],
                ]
            )

        print(table)
        return table, spot_instances

    else:
        print("No active Spot requests found.")


def _get_running_instances():
    """
    Get details of running instances
    :return: List of running instances
    """

    ec2_conn = boto3.client("ec2", region_name="us-east-1")
    filters = {"Filters": [{"Name": "state", "Values": ["active"]}]}
    spot_request = ec2_conn.describe_spot_instance_requests(**filters)
    spot_instances = list()

    if spot_request:
        for r in spot_request["SpotInstanceRequests"]:

            spot_dict = dict()
            ec2 = boto3.resource("ec2")

            instance = ec2.Instance(r["InstanceId"])
            spot_dict["instance_id"] = r["InstanceId"]
            spot_dict["id"] = r["SpotInstanceRequestId"]
            spot_dict["launch_info"] = launchtime(instance.launch_time)
            spot_dict["instance_type"] = instance.instance_type
            spot_dict["internal_ip"] = instance.private_ip_address
            spot_dict["external_ip"] = instance.public_ip_address

            tags = instance.tags

            try:
                spot_dict["user"] = [t["Value"] for t in tags if t["Key"] == "User"][0]
            except (KeyError, IndexError, TypeError):
                spot_dict["user"] = "Unknown"

            spot_instances.append(spot_dict)
    return spot_instances
