import pathlib
import sqlite3
import argparse
from core import download_file, get_download_url, get_xpn_code, WaitingSpinnerError


parser = argparse.ArgumentParser(description="EndNote parser",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-l",
                    "--limit",
                    type=int,
                    default=3,
                    help="Limit how much refs to process")
parser.add_argument("-o",
                    "--offset",
                    type=int,
                    default=0,
                    help="Refs offset amount")

parser.add_argument("data-dir",
                    help="Absolute path to *.Data directory location")
args = parser.parse_args()
config = vars(args)

limit = config['limit']
offset = config['offset']
# full path to PROJECT *.Data folder
DATA_DIR = config['data-dir']
print(f'Fetching {limit} refs with offset {offset} from {DATA_DIR}')


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

# Create a SQL connection to our SQLite database in SDB.eni file
sdb_con = sqlite3.connect(SDB_FILE)
sdb_cur = sdb_con.cursor()
# delete trigger because we cannot insert with it (it has non-existent function EN_MAKE_SORT_KEY)
sdb_cur.execute('DROP TRIGGER IF EXISTS file_res__refs_ord_AI')

# Create a SQL connection to our SQLite database in PDB.eni file
pdb_con = sqlite3.connect(PDB_FILE)
pdb_cur = pdb_con.cursor()


# read all records from target table
# The result of a "cursor.execute" can be iterated over by row
files = []

for row in sdb_cur.execute(f'SELECT id, URL FROM refs LIMIT {limit} OFFSET {offset};'):
    ref_id, url = row
    # split url by "\r" - looks like it is a delimiter
    urls = url.split('\r')
    print(f'Processing ref {ref_id}')
    for pos, url in enumerate(urls):
        # get xpn code from the link
        xpn_code = get_xpn_code(url)
        # get download_url from meta page
        download_url = get_download_url(xpn_code)
        try:
            pdf_path = download_file(PDF_DIR, download_url, ref_id)
        except WaitingSpinnerError:
            # not pdf file saved, skip
            print(f'Caught waiting spinner instead of PDF, skipping')
            continue
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
    pdb_cur.execute(f"INSERT OR IGNORE INTO pdf_index (refs_id, subkey, contents) VALUES({ref_id},'{pdf_path}',replace('\n','\n',char(10)));")
    # # update file_res in sdb
    sdb_cur.execute(f"INSERT OR IGNORE INTO file_res VALUES({ref_id},'{pdf_path}',1,{pos})")

# Be sure to close the connections
# recreate trigger
sdb_cur.execute('CREATE TRIGGER file_res__refs_ord_AI  AFTER INSERT ON file_res BEGIN UPDATE refs_ord SET (ro_key_44) = (EN_MAKE_SORT_KEY((SELECT GROUP_CONCAT(file_path) FROM (SELECT refs_id, file_path FROM file_res WHERE (refs_id = new.refs_id  ) AND (file_type = 1  OR  file_type = 2)  ORDER BY file_pos)  GROUP BY refs_id),44,12)) WHERE refs_ord.ro_id = new.refs_id; END')

# commit changes (write to db) and close connections
sdb_con.commit()
sdb_con.close()

# same for pdb
pdb_con.commit()
pdb_con.close()




