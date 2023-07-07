import os
import random
import pathlib
import sqlite3
import uuid
from urllib.parse import urlparse
import requests
import re


# we want to look like a regular internet user
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36'
headers = {'User-Agent': USER_AGENT}

# full path to initial enl file
# ENL_FILE = '/home/evgeny/devel/ipsilon-tau/UpworkVideo/ENL-Sample/Questel-2000-07-06-sample111.enl'
# DATA_DIR = '/home/evgeny/devel/ipsilon-tau/UpworkVideo/ENL-Sample/Questel-2000-07-06-sample111.Data'
DATA_DIR = 'C:/Users/waste/devel/ENL-sample-updated/Questel-2000-07-06-sample111.Data'


PDF_DIR = pathlib.Path(DATA_DIR) / 'PDF'

# contains pdf_index with pdf content
# pdf_index (pdfi_id INTEGER PRIMARY KEY AUTOINCREMENT,
#            version INTEGER UNSIGNED NOT NULL DEFAULT 0,
#            refs_id INTEGER UNSIGNED NOT NULL DEFAULT 0,
#            file_timestamp INTEGER UNSIGNED NOT NULL DEFAULT 0,
#            subkey BLOB NOT NULL,
#            contents TEXT NOT NULL DEFAULT "",
#            tag TEXT NOT NULL DEFAULT "")
# INSERT INTO pdf_index VALUES(2,0,163,0,'1785513111/Redmer.pdf',replace('\n\n','\n',char(10)),'');
PDB_FILE = pathlib.Path(DATA_DIR) / 'sdb' / 'pdb.eni'

# refs (id INTEGER PRIMARY KEY AUTOINCREMENT,
#      ... ,
#      url TEXT NOT NULL DEFAULT "")
# file_res (refs_id INTEGER NOT NULL,
#           file_path TEXT NOT NULL DEFAULT "",
#           file_type INTEGER NOT NULL,
#           file_pos INTEGER NOT NULL)
# INSERT INTO file_res VALUES(137,'1747798923/Bauer William-A coffin.pdf',1,0);
SDB_FILE = pathlib.Path(DATA_DIR) / 'sdb' / 'sdb.eni'

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


def get_random_directory():
    # generate random directory name
    directory_name = str(uuid.uuid4())
    # compose directory path inside project data folder
    directory_path = PDF_DIR / directory_name
    # create folder
    os.mkdir(directory_path)
    return directory_path


def download_file(link: str):
    response = requests.get(link, stream=True, headers=headers)
    filename = urlparse(response.url).path.split('/')[-1]
    filepath = get_random_directory() / filename
    with open(filepath, 'wb') as pdf_object:
        pdf_object.write(response.content)
    # make relative path with only last folder name in path
    relative_path = str(filepath.relative_to(filepath.parent.parent))
    return relative_path


# Create a SQL connection to our SQLite database in SDB.eni file
sdb_con = sqlite3.connect(SDB_FILE)
sdb_cur = sdb_con.cursor()
# delete trigger because we cannot insert with it (it has non-existent function EN_MAKE_SORT_KEY)
sdb_cur.execute('DROP TRIGGER IF EXISTS file_res__refs_ord_AI')
sdb_con.commit()

# Create a SQL connection to our SQLite database in PDB.eni file
pdb_con = sqlite3.connect(PDB_FILE)
pdb_cur = pdb_con.cursor()


# read all records from target table
# The result of a "cursor.execute" can be iterated over by row
files = []
for row in sdb_cur.execute('SELECT id, URL FROM refs limit 3;'):
    ref_id, url = row
    # split url by "\r" - looks like it is a delimiter
    urls = url.split('\r')
    print(f'Processing ref {ref_id}')
    for pos, url in enumerate(urls):
        # print('url=', url)
        # get xpn code from the link
        xpn_code = get_xpn_code(url)
        # get download_url from metapage
        download_url = get_download_url(xpn_code)
        # print('download_url=', download_url)
        pdf_path = download_file(download_url)
        print(f'Saved file {pdf_path} (pos {pos})')

        # collect data to files list
        files.append({
            'ref_id': ref_id,
            'pdf_path': pdf_path,
            'pos': pos
        })

# for each file update tables in sqlite
for file in files:
    ref_id = file['ref_id']
    pdf_path = file['pdf_path']
    pos = file['pos']

    # update pdf_index in pdb
    pdb_cur.execute(f"INSERT INTO pdf_index (refs_id, subkey, contents) VALUES({ref_id},'{pdf_path}',replace('\n','\n',char(10)));")
    # # update file_res in sdb
    sdb_cur.execute(f"INSERT INTO file_res VALUES({ref_id},'{pdf_path}',1,{pos})")

# Be sure to close the connections
# recreate trigger
sdb_cur.execute('CREATE TRIGGER file_res__refs_ord_AI  AFTER INSERT ON file_res BEGIN UPDATE refs_ord SET (ro_key_44) = (EN_MAKE_SORT_KEY((SELECT GROUP_CONCAT(file_path) FROM (SELECT refs_id, file_path FROM file_res WHERE (refs_id = new.refs_id  ) AND (file_type = 1  OR  file_type = 2)  ORDER BY file_pos)  GROUP BY refs_id),44,12)) WHERE refs_ord.ro_id = new.refs_id; END')

# commit changes (write to db) and close connections
sdb_con.commit()
sdb_con.close()

# same for pdb
pdb_con.commit()
pdb_con.close()




