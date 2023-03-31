from spotutil.utilities import spot_instance


def newspot(instance_type, key_pair, price, disk_size, ami_id, flux_model,
            launch_template, launch_template_version, use_on_demand):

    instance = spot_instance.Instance(instance_type, key_pair, price, disk_size, ami_id,
                                      flux_model, launch_template, launch_template_version, use_on_demand)

    instance.start()

