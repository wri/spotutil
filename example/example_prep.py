import subprocess


def main():

    # example of prepping stuff
    cwd = r'/home/ubuntu/'
    cmd = ['git', 'clone', r'https://github.com/wri/compare-imageserver-gee']

    subprocess.check_call(cmd, cwd=cwd)


if __name__ == '__main__':
    main()