from gfw_create_spot_worker.utilities import spot_instance


def newspot(instance_type, price, disk_size, ami_id):
    print instance_type

    print "instance type: {}".format(instance_type)

    instance = spot_instance.Instance(instance_type, price, disk_size, ami_id)

    instance.start()


