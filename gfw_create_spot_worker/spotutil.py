import click
from gfw_create_spot_worker.utilities import listspot, removespot, newspot


@click.group()
@click.version_option()
def spotutil():
    """."""


@spotutil.command('new')
@click.argument('instance_type')
@click.option('--price', default=3)
@click.option('--disk_size', default=500)
@click.option('--ami-id', default='ami-57990128')
def new_spot(instance_type, price, disk_size, ami_id):
    click.echo('Created new spot of type %s' % instance_type)
    newspot.newspot(instance_type, price, disk_size, ami_id)


@spotutil.command('ls')
def list_spots():
    click.echo('Listing active Spots')
    table, spot_info_list = listspot.listspot()
    print table


@spotutil.command('rm')
@click.option('--username')
@click.option('--instance_id')
@click.option('--internal_ip')
@click.option('--external_ip')
def remove_spot(instance_id, internal_ip, external_ip, username):
    removespot.removespot(username, internal_ip, external_ip, instance_id)

