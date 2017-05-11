import subprocess


def main():

    print 'calling main script'

    # call it from the directory we just cloned
    cwd = r'/home/ubuntu/compare-imageserver-gee'
    cmd = ['aws', 's3', 'cp', r's3://gfw2-data/alerts-tsv/glad/south_america_2016.csv', '.']

    subprocess.check_call(cmd, cwd=cwd)


if __name__ == '__main__':
    main()
