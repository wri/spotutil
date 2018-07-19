import boto.ec2
import boto3
from prettytable import PrettyTable


def listspot():

    ec2_conn = boto.ec2.connect_to_region('us-east-1')
    spot_request = ec2_conn.get_all_spot_instance_requests()

    client = boto3.client('ec2')
    table = PrettyTable(['User', 'Instance Type', 'Internal IP', 'External IP'])
    spot_info_list = []

    if spot_request:
        for r in spot_request:
            spot_dict = {}
            state = r.state
            if state == 'active':

                instance_id = r.instance_id
                response = client.describe_instances(InstanceIds=[instance_id])

                internal_ip = response['Reservations'][0]['Instances'][0]['PrivateIpAddress']
                external_ip = response['Reservations'][0]['Instances'][0]['PublicIpAddress']

                instance_type = ec2_conn.get_instance_attribute(instance_id, 'instanceType')['instanceType']
                try:
                    user = r.tags['User']
                except KeyError:
                    user = 'Unknown'

                table.add_row([user, instance_type, internal_ip, external_ip])

                spot_dict['instance_id'] = instance_id
                spot_dict['internal_ip'] = internal_ip
                spot_dict['external_ip'] = external_ip
                spot_dict['user'] = user
                spot_dict['id'] = r.id
                spot_info_list.append(spot_dict)

        return table, spot_info_list

    else:
        print "No active Spot requests found."
