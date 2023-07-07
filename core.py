import os
import random
from urllib.parse import urlparse
import requests
import re


# we want to look like a regular internet user
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' \
             '(KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
headers = {'User-Agent': USER_AGENT}


def get_xpn_code(link):
    # trying to get the XPN by matching with regular expression
    m = re.match(r'.*XPN=(.*)', link)
    # code is in expression group 1
    code = m.group(1)
    # return code
    return code


def get_download_url(source_xpn_code: str):
    # meta request url
    meta_url = f'https://rest.orbit.com/rest/iorbit/user/permalink/fampat/{source_xpn_code};fields=PDF'
    # make request with our headers
    response = requests.get(meta_url, headers=headers)
    # get json response
    resp_json = response.json()
    # amount of pdf documents in metadata
    amount_of_docs = len(resp_json['data']['documents'])
    # here we only expect one document
    assert amount_of_docs == 1
    # get download_url from json
    download_url = resp_json['data']['documents'][0]['PDF']
    # return download_url
    return download_url


def get_random_directory(pdf_dir: str, ref_id: int, pdf_filename):
    # seed random generator with filename and ref_id to get repeatable results
    random.seed(f'{ref_id}{pdf_filename}')
    # generate random directory name
    directory_name = random.randint(1000000000, 9999999999)
    directory_name = f'0_{directory_name}'
    # compose directory path inside project data folder
    directory_path = pdf_dir / directory_name

    # create folder, if folder already exists, then just continue
    if not os.path.exists(directory_path):
        os.mkdir(directory_path)
    return directory_path


class WaitingSpinnerError(Exception):
    pass


def download_file(pdf_dir, link: str, ref_id: int):
    response = requests.get(link, stream=True, headers=headers)
    filename = urlparse(response.url).path.split('/')[-1]

    # if we got a waiting spinner page instead of pdf raise an exception
    if filename == 'waiting-spinner.html':
        raise WaitingSpinnerError('Caught the spinner')

    filepath = get_random_directory(pdf_dir, ref_id, filename) / filename

    with open(filepath, 'wb') as pdf_object:
        pdf_object.write(response.content)
    # make relative path with only last folder name in path
    relative_path = str(filepath.relative_to(filepath.parent.parent))
    return relative_path