from __future__ import absolute_import
import click
from .utilities import listspot, removespot, newspot


@click.group()
@click.version_option()
def spotutil():
    """."""


@spotutil.command('new')
@click.argument('instance_type')
@click.argument('key_pair')
@click.option('--price', default=3)
@click.option('--disk-size', default=500)
@click.option('--ami-id', default='ami-017dc21b2db099158') #AMI for GDAL-PROCESSOR-20181109
@click.option('--flux-model', is_flag=True)   # Denotes if a spot instance for the carbon flux model should be created
@click.option('--launch-template', default='lt-00205de607ab6d4d9')  # ec2 launch template to use for flux model instance
@click.option('--launch-template-version', default="5")  # version of ec2 launch template to use for flux model instance
def new_spot(instance_type, key_pair, price, disk_size, ami_id,
             flux_model, launch_template, launch_template_version):
    newspot.newspot(instance_type, key_pair, price, disk_size, ami_id,
                    flux_model, launch_template, launch_template_version)


@spotutil.command('ls')
def list_spots():
    click.echo('Listing active spot machines')
    listspot.listspot()


@spotutil.command('rm')
@click.option('--username', help='The user printed when running `spotutil ls`')
@click.option('--internal_ip', help='The internal IP')
@click.option('--external_ip', help='The external IP')
def remove_spot(username, internal_ip, external_ip):
    removespot.removespot(username, internal_ip, external_ip)

