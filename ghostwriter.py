import re
from utils import *

class GhostWriter:

    def __init__(self):
        self.session = FuturesSession()
        resp = self.session.get(GW_URL_LOGIN, allow_redirects=False)
        self.cookies = {'csrftoken' : str(resp.result().cookies['csrftoken'])}

    
    def cookie_scrape(self): # Make this Async + dynamic
        payload = {
            'csrfmiddlewaretoken' : self.cookies['csrftoken'], 
            'login': USERNAME,
            'password': PASSWORD
        }

        req = self.session.post(GW_URL_LOGIN, data=payload, cookies=self.cookies, allow_redirects=False)
        self.cookies['sessionid'] = str(req.result().cookies['sessionid'])
        return    

    
    def download_report(self, report_id, zone_name):

        url = f'{GW_URL_REPORTING}{report_id}/docx/'
        path = 'Reports'
        if not os.path.exists(path):
            os.makedirs(path)

        report_filename = f"{path}/{PROJECT_NAME} - {PROJECT_COLOR}-box Web Application Assessment [{zone_name}]"

        with (self.session.get(url)).result() as resp:
            with open(f"{report_filename}.docx", 'wb') as f:
                f.write(resp.content)
        
        print(f"""The report "{report_filename.split("Reports/")[1]}.docx" was added to {os.getcwd()}/Reports\n""")
     

class GraphQL:

    def __init__(self):
        # Sessions
        self.session = FuturesSession()
        self.session.hooks['response'] = response_hook
        self.session.get(GQL_URL_V1)

    
    def gql_login(self):
        """Retrive JWT token for futrue requests.

        Sends a login mutation query to the GraphQL endpoint and collects the JWT token.

        Returns:
            headers (dict):  '["Authorization"]' : 'Bearer {token}'
        Raises:
            Exception: Catch exception.
    """
        
        query = """
        mutation login($username: String = "", $password: String = "") {
        login(password: $password, username: $username) {
            token
        }
        }
        """
        
        variables = {'username': USERNAME, 'password': PASSWORD}
        loginResponse = self.session.post(GQL_URL_V1, headers=HEADERS, json={'query': query, 'variables': variables})
        
        if "Invalid credentials" in loginResponse.result().text:
            sys.exit('\nInvalid Credentials.')    

        # Retrive token
        token = loginResponse.result().data.get("data").get("login").get("token")   
        HEADERS["Authorization"] = f"Bearer {token}"

    
    def get_finding_requests(self):
        """Get findings list from "OffsecFindingList" endpoint.

    Dictionary comprehension to iterate over objects in "response_to_dict['finding']".
    Places 'id' as the key and populate the values with the rest.

    Args:
        null
    Returns:
        nested_findings_dict (dict): findings in a nested dictionary. 'ID' : [{},]
    Raises:
        Exception: Catch exception.
    """


        req = self.session.get(GQL_URL_REST, headers=HEADERS)

        response_to_dict = req.result().data
        nested_findings_dict = { key['id'] : key for key in response_to_dict['finding']}

        return nested_findings_dict
    
    
    def print_findings_table(self, findings_dict):
        """Print a table for the user from the data in "nested_findings_dict", retrived from "get_findings_requests()".

        Uses PrettyTable to format the dataframe. Takes key values from "nested_findings_dict.items()"

        Args:
            nested_findings_dict (dict): the data to use.
        Returns:
            print(table) : Prints a findings dataframe table.
        Raises:
            Exception: Catch exception.
        """


        table = PrettyTable()
        table.field_names = ['ID','Finding']
        table.align = "l"
        for key, val in findings_dict.items():
            table.add_row([key, val['title']])
        print(table.get_string(sortby="Finding"))

    
    def get_user_choice(self):
        """Takes user-input of findings IDs.

        Takes a string from user-input, with the desired findings ID/s. Insures that the string dose not contain any characters except: [digits, commas, spaces].
        If the string is valid, creates a list of ID/s. 

        Args:
            choices_string (str): User-input of finding/s ID/s
        Returns:
            choices_list (list): List of user choices
        Raises:
            Loop: if choices_string == False.
        """

        while True:
            choices_string = input("Enter Findings' ID, seperated by spaces or commas: ")
            choice_valid = not(bool(re.search("[^\d|\s|,]", choices_string)))

            if choice_valid: 
                choices_list = re.split(r'[,|\s]\s*', choices_string)
                return choices_list 

            print('Please Enter Numbers Only.')
        
    
    def create_project(self):
        """Creating a new project based on user-input.

        Creates a new project based on global variables and user-input, by sending a GraphQL query. 
        It then parse the Created Project ID and the Zone shortname (I.e,. SAZ) from the response.

        Returns:
            created_project_id (str): 
            client_zone (str): 
        """

        query = """
        mutation create_project($leadId: bigint = "", $leadRoleId: bigint = "", $endDate: date = "", $engineerId: bigint = "", $engineerRoleId: bigint = "", $startDate: date = "", $clientId: bigint = "", $codename: String = "", $projectTypeId: bigint = "") {
            insert_project(objects: {startDate: $startDate, endDate: $endDate, clientId: $clientId, projectTypeId: $projectTypeId, codename: $codename, assignments: {data: [{operatorId: $leadId, endDate: $endDate, startDate: $startDate, roleId: $leadRoleId}, {operatorId: $engineerId, endDate: $endDate, startDate: $startDate, roleId: $engineerRoleId}]}}) {
            returning {
                id
                client {shortName}
            }
            }
        }"""

        variables = {
            'leadRoleId' : LEAD_ROLE_ID,
            'leadId' : LEAD_ID,
            'endDate' : END_DATE,
            'engineerId' : ENGINEER_ID,
            'engineerRoleId' : ENGINEER_ROLE_ID,
            'startDate' : START_DATE,
            'clientId' : ZONE_ID,
            'codename' : PROJECT_NAME,
            'projectTypeId' : PROJECT_TYPE
        }
    
        response = self.session.post(GQL_URL_V1, headers=HEADERS, json={'query': query, 'variables' : variables})
        # Parse project_id & zone_name from GhostWriter response 
        if 'data' in response.result().data:
            created_project_id = response.result().data.get('data').get('insert_project').get('returning')[0].get('id')
            zone_name = response.result().data.get('data').get('insert_project').get('returning')[0].get('client').get('shortName')
            return created_project_id, zone_name

        elif 'errors' in response.result().data:
            sys.exit('Client ID was not found, existing.')

        print(response.result().data)
        
    
    def escape_chars(self, finding_field):
        """Escape chars that messes GraphQL up.

        Take a string "finding_field" and adds slash to any unwanted chracters that can interfere with GraphQL syntax.

        Args:
            finding_field (str): Each finding field from the "choices_split" list.
        Returns:
            finding_field (list): List of user choices
        """

        matches = ['\\', '"']
        if any(value in finding_field for value in matches):
            for replace in (("\\", "\\\\"), ('"', '\\"')):
                finding_field = finding_field.replace(*replace)
        return finding_field

    
    def choices_to_report(self, choices_split, nested_findings_dict):
        """Populate findings fields based on user_choices.

        Iterates over "choices_split" list and fetches the values of each field based on the finding (choice) ID, and appends it to "graphql_finding_query".
        The "escape_chars" function is invoked for each field that returns a string, for syntax sake.
        It then does string manipulating to match GraphQL syntax, and returns the final query.

        Args:
            choices_split (list): User-input of finding/s ID/s
            nested_findings_dict (dict): A nested dictionary with all the findings.
        Returns:
            final_finding_query (list): Ready to use GraphQL query.
        """
        
        try:
            # import ipdb; ipdb.set_trace()
            if not choices_split:
                sys.exit(f'[+] No relevant findings in {sys.argv[1]}')

            prepare_create_report = []
            for choice in choices_split:
                finding_description = self.escape_chars(nested_findings_dict[int(choice)]['description'])
                finding_impact = self.escape_chars(nested_findings_dict[int(choice)]['impact'])
                finding_mitigation = self.escape_chars(nested_findings_dict[int(choice)]['mitigation'])
                finding_rep_step = self.escape_chars(nested_findings_dict[int(choice)]['replication_steps'])
                finding_title = self.escape_chars(nested_findings_dict[int(choice)]['title'])
                finding_references = f"<ul>{self.escape_chars(nested_findings_dict[int(choice)]['url'])}</ul>"
                finding_severity = nested_findings_dict[int(choice)]['severityId']

                graphql_finding_query = """
                {{title: "{finding_title}", description: "{finding_description}", impact: "{finding_impact}", mitigation: "{finding_mitigation}", references: "{finding_references}", replication_steps: "{finding_rep_step}", severityId: "{finding_severity}"}}
                """.format(finding_title=finding_title, finding_description=finding_description, finding_impact=finding_impact, finding_mitigation=finding_mitigation, finding_references=finding_references, finding_rep_step=finding_rep_step, finding_severity=finding_severity)

                prepare_create_report.append(graphql_finding_query.replace('\n\t',''))
                remove_double_quotes = ', '.join(prepare_create_report)
                final_finding_query = str.join(" ", remove_double_quotes.splitlines())
                
            return final_finding_query

        except KeyError:
            sys.exit(f'[+] No files were found in {sys.argv[1]} folder.')    

    
    def create_report(self, created_project_id, final_finding_query):

        """Creating a new report based on user-input.

        Iterates over "choices_split" list and fetches the values of each field based on the finding (choice) ID, and appends it to "graphql_finding_query".
        The "escape_chars" function is invoked for each field that returns a string, for syntax sake.
        It then does string manipulating to match GraphQL syntax, and returns the final query.

        Args:
            created_project_id (str): The created project ID from the "create_project" function.
            final_finding_query (dict): Inject the "final finding query" to the query.
        Returns:
            Project ID
            Report ID
            Report Findings
            Report Download Link
        """

        query = """
            mutation create_report($template_last_update: date = "", $title: String = "", $projectId: bigint = "", $pptxTemplateId: bigint = "", $docxTemplateId: bigint = "") {{
            insert_report(objects: {{title: $title, projectId: $projectId, pptxTemplateId: $pptxTemplateId, docxTemplateId: $docxTemplateId, last_update: $template_last_update, findings: {{data: [{final_finding_query}]}}}}) {{
                returning {{
                id
                findings {{title}}
                }}
            }}
            }}
        """.format(final_finding_query=final_finding_query)

        variables = {
        'docxTemplateId' : DOCX_TEMPLATE,
        'template_last_update' : DOCX_LAST_UPDATE,
        'pptxTemplateId' : PPTX_TEMPLATE,
        'projectId' : created_project_id,
        'title' : PROJECT_NAME
        }

        response = self.session.post(GQL_URL_V1, headers=HEADERS, json={'query': query, 'variables' : variables}) 

        # Returns the value of "returning" key into a list variable
        response_returning_list = response.result().data.get('data').get('insert_report').get('returning')

        # Creates a list from 'title' key from the above list
        title_list = '\n [+] '.join([x.get('title') for x in response_returning_list[0].get('findings')])

        created_report_id = response_returning_list[0].get('id')

        if '{"returning" : [{"id":' in response.result().text:
            print("\nThe report was created successfully.")
            print(f"________________________________________")
            print(f"Report Findings:\n [+] {title_list}")
            # print(f'\nThe report was downloaded to {os.getcwd()}/Reports')
            print(f'\nReport Link: {GW_URL_REPORTING}{created_report_id}/docx/')
            return response_returning_list[0].get('id')
        elif 'Error: not a valid graphql query' in response.text:
            print(f"\n {response.result().data.get('errors')[0].get('message')}")
        else:
            print(response.text)
