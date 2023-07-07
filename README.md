# Endnote parser script

## Install python
    
    https://www.python.org/ -> Downloads -> Download for Windows -> <Python 3.11.4>

## Install poetry
    
    curl -sSL https://install.python-poetry.org | python -
    # add poetry dir to Path variable
    C:\Users\<username>\AppData\Roaming\Python\Scripts

## Install git
   
    https://git-scm.com/download/win -> <64-bit Git for Windows Setup> -> install

## Clone project

    mkdir devel
    cd devel
    git clone https://github.com/ipsilon-tau/endnote-parser.git

## Install dependencies

    cd endnote-parser
    poetry install

## Run the program

    # limit downloading to only 3 references
    poetry run python main.py --limit 3 /home/user/ENL-Sample/Questel-2000-07-06-sample111.Data

    # limit downloading to only 3 references offset 10 (skip 10 records from the beginning)
    poetry run python main.py --limit 3 --offset 10 /home/user/ENL-Sample/Questel-2000-07-06-sample111.Data

    # limit downloading to 75 references
    # set http request timeout 5 seconds
    poetry run python -u main.py --timeout 5 --limit 75 /home/user/ENL-Sample/Questel-2000-07-06-sample111.Data
