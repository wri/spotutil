from spotutil.utilities import spot_instance


def newspot(instance_type, price, disk_size, ami_id):

    instance = spot_instance.Instance(instance_type, price, disk_size, ami_id)

    instance.start()

