import click
from utilities import listspot, removespot, newspot


@click.group()
@click.version_option()
def spotutil():
    """."""


@spotutil.command('new')
@click.argument('instance_type')
@click.option('--price', default=3)
@click.option('--disk_size', default=500)
@click.option('--ami-id', default='ami-032ce1c805826aa16') #AMI for GDAL-PROCESSOR-20181108
def new_spot(instance_type, price, disk_size, ami_id):
    newspot.newspot(instance_type, price, disk_size, ami_id)


@spotutil.command('ls')
def list_spots():
    click.echo('Listing active Spots')
    listspot.listspot()


@spotutil.command('rm')
@click.option('--username', help='The user printed when running `spotutil ls`')
@click.option('--internal_ip', help='The internal IP')
@click.option('--external_ip', help='The external IP')
def remove_spot(username, internal_ip, external_ip):
    removespot.removespot(username, internal_ip, external_ip)

