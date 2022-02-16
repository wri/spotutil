from __future__ import print_function
from spotutil.utilities.listspot import listspot
import boto3


def removespot(username=None, internal_ip=None, external_ip=None, instance_type=None):

    client = boto3.client('ec2', 'us-east-1')

    # get list of active spots
    table, spot_list = listspot()

    # turn inputs in a dict, can then find matching input
    inputs = {'user': username, 'internal_ip': internal_ip, 'external_ip': external_ip, 'instance_type': instance_type}

    inputs = dict((k, v) for k, v in inputs.items() if v is not None)

    spot_filter_key = list(inputs.keys())[0]
    spot_filter_val = inputs[spot_filter_key]
    found_match = None

    for request in spot_list:

        if request[spot_filter_key] == spot_filter_val:
            found_match = True
            print("Canceling this spot request: {}".format(request))

            instance_id = request['instance_id']

            client.terminate_instances(InstanceIds=[instance_id])

            response = client.cancel_spot_instance_requests(SpotInstanceRequestIds=[request['id']])
            status = response[u'CancelledSpotInstanceRequests'][0]['State']
            print("Status of request to cancel spot: {}".format(status))

    if not found_match:
        print("WARNING: There are no active spot instances with {0} of {1}".format(spot_filter_key, spot_filter_val))
