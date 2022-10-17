#!/usr/local/bin/python3
import traceback
from utils import *
from azstorage import *
from ghostwriter import *
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import current_thread, get_ident, get_native_id

def main(): 
    # Initialize Objects
    azureManage = AzureManage()
    ghostWriter = GhostWriter()
    graphQL = GraphQL()    

    try:
        # -----------------------
        #  GhostWriter & GraphQL
        # -----------------------

        # Grab tokens for GhostWrtier & GraphQL
        ghostWriter.cookie_scrape()
        graphQL.gql_login()


        # Get & Print Findings
        nested_findings_dict = graphQL.get_finding_requests()


        # Match dirs name to findings
        dirs_list = dirs_to_choices(nested_findings_dict)
        

        # Create Projectc
        created_project_id, zone_name = graphQL.create_project()

        # -----------------------
        #         Azure 
        # -----------------------

        zone_name = zone_name.lower() # afr

        connect_str, acc_key = azureManage.retrieve_a_secret(VAULT_URL, VAULT_CONN_STR, VAULT_KEY)
        dl_client = DataLakeServiceClient.from_connection_string(connect_str)
        fs_client = dl_client.get_file_system_client(file_system=zone_name)


        if not fs_client.exists():
            fs_client.create_file_system()
            print(f'[+] Creating "{zone_name}" container.')
        

        # lists all files under "PATH" and upload them using theards
        all_files = []
        for root, dirs, files in os.walk(PATH):
            for file in files:
                if not file.startswith('.'):
                    all_files.append(os.path.join(root, file))
        
        # if no files wer'e found
        if not all_files:
            sys.exit(f'[+] No files were found in {sys.argv[1]} folder.')

        with ThreadPoolExecutor() as executor:
            for file in all_files:
                    executor.submit(azureManage.upload_files, file, fs_client)


        urls = {}
        paths = fs_client.get_paths(path=FOLDER_NAME)
        for path in paths:
            if path['is_directory'] == False:
                url_token = azureManage.generate_sas_token(ACCOUNT_NAME, acc_key, zone_name, path['name'])

                # Get the directory name of the uploaded finding 
                directory_name = path.name.split('/')[-2] 

                # Check if links[key] exists. If not, create one with a list object as its value and append the url to the list.
                urls[directory_name] = urls.get(directory_name, [])
                urls[directory_name].append(f"""<li><a href="{url_token}">{url_token.split('?')[0].split('/')[-1]}</a></li>""")


        # Insert links into the relevant finding in "nested_findings_dict"
        urls_to_dict(urls, nested_findings_dict)

        # Prepare Choices and Create Report
        final_finding_query = graphQL.choices_to_report(dirs_list, nested_findings_dict)
        report_id = graphQL.create_report(created_project_id, final_finding_query)

        # Download Report
        ghostWriter.download_report(report_id, zone_name)


    except KeyboardInterrupt:
        print('\nKeyboard Intertfere. Closing.')
    except Exception as e:
        print(traceback.format_exc())


if __name__ == "__main__":
    main()
