from utils import *
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient
from azure.storage.blob import generate_blob_sas, BlobSasPermissions


class AzureManage:
        
    def __init__(self):        
        pass


    def retrieve_a_secret(self, VAULT_URL, VAULT_CONN_STR, VAULT_KEY):
        # retrieves the conn-str and the acc_key from Key Vault
        
        credentials = DefaultAzureCredential()
        secret_client = SecretClient(vault_url=VAULT_URL, credential=credentials)
        secret_conn = secret_client.get_secret(VAULT_CONN_STR)
        secret_key = secret_client.get_secret(VAULT_KEY)
        
        return secret_conn.value, secret_key.value

    
    def upload_files(self, file, fs_client):
        # Uploads all files to Azure DataLake Storage

        try:
            file_split = file.split(PATH + '/' )[1] # Removes the user-supplied path from the file path. Needed for create_file
            dir_client = fs_client.get_directory_client(f'{date.today().year}/{PROJECT_NAME}')
            with open(file, 'rb') as f: 
                file_content = f.read()
                create_file = dir_client.create_file(file_split) 
                create_file.upload_data(file_content, overwrite=True)
            
        except Exception as e:
            print("Failed to upload files. Error: " + str(e))

    
    def generate_sas_token(self, ACCOUNT_NAME, VAULT_KEY, ZONE_NAME, FILE_NAME):
    # generates a shared access signature (sas) to files
            sas = generate_blob_sas(account_name=ACCOUNT_NAME,
                                    account_key=VAULT_KEY,
                                    container_name=ZONE_NAME,
                                    blob_name=FILE_NAME,
                                    permission=BlobSasPermissions(read=True),
                                    expiry=datetime.utcnow() + timedelta(days=365))
            sas_url ='https://'+ACCOUNT_NAME+'.blob.core.windows.net/'+ZONE_NAME+'/'+FILE_NAME+'?'+sas
            return sas_url
