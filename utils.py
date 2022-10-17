import os,logging, sys, getpass, readline
from datetime import datetime, date, time, timedelta
from prettytable import PrettyTable
from requests_futures.sessions import FuturesSession

# -----------------------
#       Arguments 
# -----------------------

if len (sys.argv) != 2 :
    print("Usage: python3 x-port.py <path/to/findings-directory>\n")
    sys.exit ()
    
PATH = sys.argv[1]

# -----------------------
#        Globals 
# -----------------------

# Environmental Credentials for GhostWriter & GraphQL
ENV_USER = os.environ.get('GW_USER')
ENV_PASS = os.environ.get('GW_PASS')

# Set Credentials
if ENV_USER and ENV_PASS:
    USERNAME = ENV_USER
    PASSWORD = ENV_PASS

else:
    USERNAME = input('Enter Your GhostWriter Username: ')
    PASSWORD = getpass.getpass(prompt='Enter Your Password: ')

# -----------------------
#      x-port logo 
# -----------------------
print('''    
-------------------------------------------------------------------

        ____  __        ________ _______ ________ ________
        __  |/ /        ___  __ \__  __ \___  __ \___  __/
        __    / __________  /_/ /_  / / /__  /_/ /__  /   
        _    |  _/_____/_  ____/ / /_/ / _  _, _/ _  /    
        /_/|_|          /_/      \____/  /_/ |_|  /_/  
           

    X-PORT --> Automated Reports ( @practiccollie | @ta1c0 )
-------------------------------------------------------------------
''')

# -----------------------
#        Prompts 
# -----------------------

print("""Hello,
Please make sure to fill in the following prompts, the rest is on me.\n""")

CODENAME_PROMPT = """[+] Please enter your project's name - (e.g., google.com): """

START_DATE_PROMPT = """[+] Please enter your project's start-date - (e.g., 2022-08-30): """

END_DATE_PROMPT = """[+] Please enter your project's end-date - (e.g., 2022-08-31): """

### Replace with your sites
GLOBAL_SITES_PROMPT = """
Sites
----------------
  US : 1
  AFR : 2
  EUR : 3
  ASIA : 4

[+] Please Enter Site ID: """

### Replace with your team memebers names
TEAM_MEMBER_PROMPT = """ 
Team Members IDs
----------------
  name_1 : 1 
  name_2 : 2

[+] Please select team member/s ID: """
    
# -----------------------
#        GraphQL 
# -----------------------

# HTTP
GQL_URL = 'http://<YOUR-SITE.com>:8080' ### Replace with your GraphQL endpoint
GQL_URL_V1 = GQL_URL + '/v1/graphql'
GQL_URL_REST = GQL_URL + '/api/rest/<YOUR-ENDPOINT>' ### Replce ywith your findings endpoint

HEADERS = {"Content-Type": "application/json", }

# Template
DOCX_TEMPLATE = '2' ### Replace with your DOCX template ID
PPTX_TEMPLATE = '2' ### Replace with your PPTX template ID
DOCX_LAST_UPDATE = '2022-09-04' ### Replace with your DOCX last update date

# Team Members
LEAD_ID = '1' ### Replace with your lead team ID
LEAD_ROLE_ID = '1' ### Replace with your lead team role ID
ENGINEER_ROLE_ID = '1' ### Replace with your engineer role ID

# Project
PROJECT_TYPE = '4' ### Web Application Assessment

ZONE_ID = input(GLOBAL_SITES_PROMPT)
PROJECT_NAME = input(CODENAME_PROMPT)
START_DATE = input(START_DATE_PROMPT)
END_DATE = input(END_DATE_PROMPT)
ENGINEER_ID = input(TEAM_MEMBER_PROMPT)
PROJECT_COLOR = input('\nEnter Assessment Type - Black/Grey/White: ')

# -----------------------
#       GhostWriter 
# -----------------------

GW_URL = 'http://<YOUR-SITE.com>:8000' ### Replace with your GhostWriter login page
GW_URL_LOGIN = GW_URL + '/accounts/login/'
GW_URL_REPORTING = GW_URL + '/reporting/reports/'

# -----------------------
#         Azure 
# -----------------------

VAULT_URL = "https://<your-azure-vault-name>.vault.azure.net/" ### Replace with your Azure keyvault URL
VAULT_CONN_STR = "<vault-connection-string>" ### Replace with your vault connection string
VAULT_KEY= "<vault-key>" ### Replace with your vault key
FOLDER_NAME = f'{date.today().year}/{PROJECT_NAME}'
ACCOUNT_NAME= "<storage-account-name>" ### Replace with your storage account name

# -----------------------
#     Util Functions 
# -----------------------

def urls_to_dict(links, dictionary):
    # Need to add docstring
    
    for key, value in dictionary.items(): 
        for key2, value2 in links.items():
            if key2.lower() in value['title'].lower():
                dictionary[key]['url'] = "".join(value2)


def dirs_to_choices(dictionary):
    # Need to add docstring

    dirs = [file.name for file in os.scandir(PATH) if file.is_dir()]

    id_list = []
    for key, value in dictionary.items():
        for dir in dirs:
            if dir.lower() in value['title'].lower():
                id_list.append(key)
    return id_list


def response_hook(resp, *args, **kwargs):
    # Parse JSON from the Futures.result() to Dictionary 

    resp.data = resp.json()
