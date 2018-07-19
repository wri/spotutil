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
    newspot.newspot(instance_type, price, disk_size, ami_id)


@spotutil.command('ls')
def list_spots():
    click.echo('Listing active Spots')
    table, spot_info_list = listspot.listspot()
    print table


@spotutil.command('rm')
@click.option('--username', help='The user printed when running `spotutil ls`')
@click.option('--internal_ip', help='The internal IP')
@click.option('--external_ip', help='The external IP')
def remove_spot(username, internal_ip, external_ip):
    removespot.removespot(username, internal_ip, external_ip)
