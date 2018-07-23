import boto.ec2
import boto3
from prettytable import PrettyTable

from util import launchtime


def listspot():

    ec2_conn = boto.ec2.connect_to_region('us-east-1')
    spot_request = ec2_conn.get_all_spot_instance_requests()

    client = boto3.client('ec2')
    table_columns = ['User', 'Instance Type', 'Internal IP', 'External IP', 'Up Time']
    table = PrettyTable(table_columns)
    for c in table_columns:
        table.align[c] = "l"

    spot_info_list = []

    if spot_request:
        for r in spot_request:
            spot_dict = {}
            state = r.state
            if state == 'active':

                instance_id = r.instance_id
                response = client.describe_instances(InstanceIds=[instance_id])
                try:
                    internal_ip = response['Reservations'][0]['Instances'][0]['PrivateIpAddress']
                except:
                    internal_ip = 'Unknown'
                try:
                    external_ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']
                except:
                    external_ip = 'Unknown'
                launch_info = launchtime(response, r)

                instance_type = ec2_conn.get_instance_attribute(instance_id, 'instanceType')['instanceType']
                try:
                    user = r.tags['User']
                except KeyError:
                    user = 'Unknown'

                table.add_row([user, instance_type, internal_ip, external_ip, launch_info])

                spot_dict['instance_id'] = instance_id
                spot_dict['internal_ip'] = internal_ip
                spot_dict['external_ip'] = external_ip
                spot_dict['user'] = user
                spot_dict['id'] = r.id
                spot_info_list.append(spot_dict)

        print table
        return table, spot_info_list

    else:
        print "No active Spot requests found."

