from spotutil.utilities import spot_instance


def newspot(instance_type, key_pair, price, disk_size, ami_id, flux_model):

    instance = spot_instance.Instance(instance_type, key_pair, price, disk_size, ami_id, flux_model)

    instance.start()
