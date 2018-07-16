import requests


def in_office():
    
    # check our external IP
    # if we're out of the office, will have to use private IP and VPN

    in_office = False

    # https://stackoverflow.com/a/36205547/4355916
    r = requests.get('https://api.ipify.org')
    ip = r.text

    if ip == '216.70.220.184':
        in_office = True

    return in_office

