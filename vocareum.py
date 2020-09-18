"""
GNU General Public License v3.0

Copyright (C) 2007 Free Software Foundation, Inc. <https://fsf.org/>
Everyone is permitted to copy and distribute verbatim copies
of this license document, but changing it is not allowed.

by py-paulo
"""

import sys
try:
    import requests
except ModuleNotFoundError:
    sys.exit('please install the package: requests')
import re
import os
import getpass
from pathlib import Path
try:
    from rich.console import Console
    from rich.markdown import Markdown
except ModuleNotFoundError:
    sys.exit('please install the package: rich')

MARKDOWN = """
# python script ``vocareum``

Bom, segundo a descrição no site https://labs.vocareum.com, Vocareum é uma plataforma que possui
laboratórios de nuvem para aprendizado utilizam a infraestrutura de nuvem para permitir que os 
alunos estejam a um clique de aplicativos de codificação. 

### Motivações

Tenho uma conta estudantil e sempre que precisava usar o aws-cli tinha que acessar o site e salvar as credenciais que 
expiram no `~/.aws/credentials` manualmente, e isso é bem chato,
então resolvi automatizar criando um script para fazer isso.

> Você precisa do arquivo `config` no `~/.aws/`, caso não tenha basta executar o comando `aws configure`

1. Você precisa do `Python` com a biblioteca `requests`
2. O aws cli instalado na sua máquina

```
usage: %s email
```
""" % Path(sys.argv[0]).name

proxies = {
    "http": "http://127.0.0.1:8080",
    "https": "https://127.0.0.1:8080",
}

PATH_AWS_CREDENTIALS = Path.home().joinpath('.aws', 'credentials')
try:
    PATH_AWS_CREDENTIALS.mkdir(parents=True, exist_ok=True)
except FileExistsError:
    pass

URL = 'https://labs.vocareum.com'
URL_LOGIN = URL + '/util/vcauth.php'
URL_LOGIN_GET = URL + '/home/login.php?code=&e=Please%20enter%20a%20valid%20email%20address'
URL_GET_AWS_ACCESS = URL + '/util/vcput.php?a=getaws&nores=1&stepid=14335&mode=s&type=0&vockey=%s'
URL_HOME_PAGE = URL + '/main/main.php?m=editor&nav=1&asnid=14334&stepid=14335'

wl = ['PHPSESSID', 'logintoken', 'tokenExpire', 'usertoken', 'userid', 'userassignment', 'domain_latestWebProxy']

headers = {
    'Host': 'labs.vocareum.com',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:77.0) Gecko/20100101 Firefox/77.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Origin': URL
}


def try_login(mail, password):
    rq = requests.get(url=URL_LOGIN_GET, headers=headers)
    cookies = rq.headers.get('Set-Cookie')
    cfduid = cookies.split(';')[0].split('=')
    cookie = {cfduid[0]: cfduid[1]}

    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    headers['Referer'] = 'https://labs.vocareum.com/home/login.php?code=&e=Please%20enter%20a%20valid%20email%20address'
    headers['DNT'] = '1'

    datapost = 'sender=home&loginid=%s&passwd=%s' % (mail, password)
    datapost = datapost.replace('@', '%40')

    headers['Content-Length'] = str(len(datapost))
    headers['Connection'] = 'Close'
    headers['Cookie'] = '='.join(cfduid)

    rq = requests.post(url=URL_LOGIN, data=datapost, headers=headers, cookies=cookie, allow_redirects=False)

    cookies = rq.headers.get('Set-Cookie')
    vockey = re.findall(r'\w{32}', cookies)[0]

    headers.pop('Content-Type')
    headers.pop('Content-Length')
    headers.pop('Cookie')

    new_cookies = {cfduid[0]: cfduid[1]}

    for item in wl:
        for ck in cookies.split(';'):
            if item in ck:
                tmp = ck.replace('Secure, ', '').split('=')
                new_cookies[tmp[0]] = tmp[1]

    rq = requests.get(url=URL_HOME_PAGE, headers=headers, cookies=new_cookies)

    proxy = re.findall(
        r'https://proxy.vocareum.com/hostip/(?:[0-9]{1,3}\.){3}[0-9]{1,3}:[0-9]{1,5}/vocproxy/[\w|.]{10,70}',
        rq.text)
    proxy = 'https://proxy.vocareum.com/hostip/172.31.18.122:5000/vocproxy/72448074974689574689514335015eee0b738955c4' \
            '.96014152' if len(proxy) == 0 else proxy[0]

    new_cookies['domain_latestWebProxy'] = proxy

    headers['Referer'] = 'https://labs.vocareum.com/main/main.php'
    headers['X-Requested-With'] = 'XMLHttpRequest'

    rq = requests.get(url=URL_GET_AWS_ACCESS % vockey, headers=headers, cookies=new_cookies)

    aws_credentials = rq.text

    aws_access_key_id = re.findall(r'aws_access_key_id=(.*)', aws_credentials)[0]
    aws_secret_access_key = re.findall(r'aws_secret_access_key=(.*)', aws_credentials)[0]
    aws_session_token = re.findall(r'aws_session_token=(.*)', aws_credentials)[0]

    aws_write_lines = ['aws_access_key_id=%s' % aws_access_key_id, 'aws_secret_access_key=%s' % aws_secret_access_key,
                       'aws_session_token=%s' % aws_session_token]

    for line in aws_write_lines:
        print(line)

    os.remove(PATH_AWS_CREDENTIALS)

    with open(PATH_AWS_CREDENTIALS, 'w+') as fp:
        fp.write('[default]\n')

        for line in aws_write_lines:
            fp.write('%s\n' % line)


if __name__ == '__main__':
    console = Console()
    md = Markdown(MARKDOWN)

    console.print(md)

    if len(sys.argv) >= 2:
        passwd = getpass.getpass()
        try_login(sys.argv[1], passwd)
    else:
        pass

