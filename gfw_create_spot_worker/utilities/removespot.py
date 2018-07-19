from gfw_create_spot_worker.utilities.listspot import listspot
import boto3


def removespot(username=None, internal_ip=None, external_ip=None):

    client = boto3.client('ec2')

    # get list of active spots
    table, spot_list = listspot()

    # turn inputs in a dict, can then find matching input
    inputs = {'user': username, 'internal_ip': internal_ip, 'external_ip': external_ip}

    inputs = dict((k, v) for k, v in inputs.iteritems() if v is not None)
    spot_filter_key = inputs.keys()[0]
    spot_filter_val = inputs[spot_filter_key]
    found_match = None
    for request in spot_list:

        if request[spot_filter_key] == spot_filter_val:
            found_match = True
            print "canceling this spot request: {}".format(request)

            instance_id = request['id']

            response = client.cancel_spot_instance_requests(SpotInstanceRequestIds=[instance_id])
            status = response[u'CancelledSpotInstanceRequests'][0]['State']
            print "Status of request to Cancel Spot: {}".format(status)

    if not found_match:
        print "WARNING: There are no active spot instances with {0} of {1}".format(spot_filter_key, spot_filter_val)
