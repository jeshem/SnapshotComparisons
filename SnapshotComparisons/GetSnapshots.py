import oci
import sys
import datetime
from PrintUsage import print_usage

class get_snapshot(object):

    C_IDENTITY = 'identity'
    C_IDENTITY_ADS = 'availability_domains'
    C_IDENTITY_TENANCY = 'tenancy'
    C_IDENTITY_COMPARTMENTS = 'compartments'
    C_IDENTITY_REGIONS = 'regions'

    C_LIMITS = "limits"
    C_LIMITS_SERVICES = "services"
    C_LIMITS_QUOTAS = "quotas"

    data = {}
    compartment_data = {}

    services = []

    limit_data = []
    quota_data = []
    usage_data = {}

    service_list = []
    
    scope_list = []             # limit what regions to look, specify in config   
    bAllScope = True            # assume cover all regions

    warning = 0

    #For Windows, use \\. For Mac/Linux, use /
    path_separator = "/"

    usage_location = r"/Users/edwardcheng/Desktop/NSOCI usages"

    def __init__(self):
        #path to your config file
        self.config_file = oci.config.DEFAULT_LOCATION

        #select the profile you want to use from your config file
        #self.config_section = oci.config.DEFAULT_PROFILE
        self.config_section = "ORACLENETSUITE"

        self.create_signer(self.config_file, self.config_section)
        self.load_identity_main()
        tenancy = self.get_tenancy()
        self.main_menu()

    ##########################################################################
    # Create signer
    ##########################################################################
    def create_signer(self, file, section):
        try:
            self.config = oci.config.from_file(file, section)
            self.signer = oci.signer.Signer(
                tenancy=self.config["tenancy"],
                user=self.config["user"],
                fingerprint=self.config["fingerprint"],
                private_key_file_location=self.config.get("key_file"),
                pass_phrase=oci.config.get_config_value_or_default(self.config, "pass_phrase"),
                private_key_content=self.config.get("key_content")
            )
            
            # ECC: region scope
            try:
                scopeStr = self.config['scope']
            except:
                scopeStr = ''
                
            scopeStr = scopeStr.strip().lower()
            if scopeStr == '':
                scopeStr = "all"
                
            print("Get info in these regions: " + scopeStr + "\n")
            if (scopeStr != 'all'):
                self.bAllScope = False
                self.scope_list = scopeStr.split(";")
        except:
            sys.exit("Error creating signer from config file. Please check your config file and try again.")

    ##########################################################################
    # Initialize data key
    ##########################################################################
    def initialize_data_key(self, module, section):
        if module not in self.data:
            self.data[module] = {}
        if section not in self.data[module]:
            self.data[module][section] = []


    ##########################################################################
    # Load oci region data
    ##########################################################################
    def load_oci_region_data(self, region_name):

        # Assign Region to config file
        self.config['region'] = region_name
        self.signer.region = region_name

        self.load_limits_main()


    ##########################################################################
    # Identity Module
    ##########################################################################
    def load_identity_main(self):
        try:
            # create identity object
            identity = oci.identity.IdentityClient(self.config, signer=self.signer)

            # get tenancy id from the config file
            tenancy_id = self.get_tenancy_id()
            self.data[self.C_IDENTITY] = {}

            # load tenancy and compartments
            self.load_identity_tenancy(identity, tenancy_id)
            self.load_identity_compartments(identity)

            
        except oci.exceptions.RequestException:
            raise
        except oci.exceptions.ServiceError:
            raise
        except Exception as e:
            print("error in __load_identity_main: ", str(e))
            raise


    ##########################################################################
    # Load tenancy
    ##########################################################################
    def load_identity_tenancy(self, identity, tenancy_id):
        try:
            tenancy = identity.get_tenancy(tenancy_id).data
            try:
                sub_regions = identity.list_region_subscriptions(tenancy.id).data
            except oci.exceptions.ServiceError as e:
                if self.__check_service_error(e.code):
                    self.__load_print_auth_warning()
                else:
                    raise

            data_subs = []
            print ("Regions subscribed by oraclenetsuite tenanacy: ")
            for es in sub_regions:
                data_subs.append(str(es.region_name))
                print ("   " + str(es.region_name))
                
            data = {
                'id': tenancy.id,
                'name': tenancy.name,
                'home_region_key': tenancy.home_region_key,
                'subscribe_regions': str(', '.join(x for x in data_subs)),
                'list_region_subscriptions': data_subs
            }
            self.data[self.C_IDENTITY][self.C_IDENTITY_TENANCY] = data

        except oci.exceptions.RequestException:
            raise
        except Exception as e:
            raise Exception("Error in load_identity_tenancy: " + str(e.args))
            raise

    ##########################################################################
    # Load limits main
    ##########################################################################
    def load_limits_main(self):

        self.limits_client = oci.limits.LimitsClient(self.config, signer=self.signer)
        self.quotas_client = oci.limits.QuotasClient(self.config, signer=self.signer)

        self.initialize_data_key(self.C_LIMITS, self.C_LIMITS_SERVICES)
        self.initialize_data_key(self.C_LIMITS, self.C_LIMITS_QUOTAS)

    ##########################################################################
    # load limits
    ##########################################################################
    def load_limits(self, limits_client, tenancy_id):     
        
        #If the services have not been retrieved yet, retrieve them
        if not self.services:
            self.build_services_list(limits_client, tenancy_id)

        # oci.limits.models.ServiceSummary
        for service in self.services:
            print(".", end="")

            # get the limits per service
            limits = []
            try:
                limits = oci.pagination.list_call_get_all_results(limits_client.list_limit_values, tenancy_id, service_name=service.name, sort_by="name").data
            except Exception as e:
                if self.__check_service_error(e.code):
                    self.__load_print_auth_warning("a", False)
                else:
                    raise

            # oci.limits.models.LimitValueSummary
            for limit in limits:
                val = {
                    'name': str(service.name),
                    'description': str(service.description),
                    'limit_name': str(limit.name),
                    'availability_domain': (" " if limit.availability_domain is None else str(limit.availability_domain)),
                    'scope_type': str(limit.scope_type),
                    'limit': int(limit.value),
                    'used': 0,
                    'available': 0,
                    'region_name': str(self.config['region'])
                }

                # if not limit, continue, don't calculate limit = 0
                if limit.value == 0:
                    continue

                # get usage per limit if available
                try:
                    usage = []
                    if limit.scope_type == "AD":
                        usage = limits_client.get_resource_availability(service.name, limit.name, tenancy_id, availability_domain=limit.availability_domain).data
                    else:
                        usage = limits_client.get_resource_availability(service.name, limit.name, tenancy_id).data

                    # oci.limits.models.ResourceAvailability
                    if usage.used:
                        val['used'] = int(usage.used)
                    if usage.available:
                        val['available'] = int(usage.available)
                except Exception:
                    raise

                print (
                    (val['name'] + " ").ljust(20) +
                    (val['limit_name']).ljust(37) +
                    ("Limit= " + str(val['limit'])).ljust(20) +
                    ("Used= " + str(val['used'])).ljust(20) + 
                    ("Available= " + str(val['available'])).ljust(20) +
                    (val['availability_domain']).ljust(20)
                    )
                # add to array
                self.limit_data.append(val)

    ##########################################################################
    # get compartment usages, limits, etc.
    ##########################################################################
    def load_compartment_usage(self, limits_client, compartment_id, tenancy_id):        
        compartment_usage = []
        if not self.services:
            self.build_services_list(limits_client, tenancy_id)

        # oci.limits.models.ServiceSummary
        for service in self.services:
            # get the limits per service
            limits = []
            try:
                limits = oci.pagination.list_call_get_all_results(limits_client.list_limit_values, tenancy_id, service_name=service.name, sort_by="name").data
            except Exception as e:
                print("Unexpected error: " + str(e))
                raise

            # oci.limits.models.LimitValueSummary
            for limit in limits:
                val = {
                    'name': str(service.name),
                    'description': str(service.description),
                    'limit_name': str(limit.name),
                    'availability_domain': ("" if limit.availability_domain is None else str(limit.availability_domain)),
                    'scope_type': str(limit.scope_type),
                    'limit': int(limit.value),
                    'used': 0,
                    'available': 0,
                    'region_name': str(self.config['region']),
                    'compartment_id': str(compartment_id)
                }

                # if not limit, continue, don't calculate limit = 0
                if limit.value == 0:
                    continue

                # get usage per limit if available
                try:
                    usage = []
                    if limit.scope_type == "AD":
                        usage = limits_client.get_resource_availability(service.name, limit.name, compartment_id, availability_domain=limit.availability_domain).data
                    else:
                        usage = limits_client.get_resource_availability(service.name, limit.name, compartment_id).data

                    # oci.limits.models.ResourceAvailability
                    if usage.used:
                        val['used'] = int(usage.used)
                    if usage.available:
                        val['available'] = int(usage.available)
                except Exception:
                    pass

                print (
                    (val['name'] + " ").ljust(20) +
                    (val['limit_name']).ljust(37) +
                    ("Limit= " + str(val['limit'])).ljust(20) +
                    ("Used= " + str(val['used'])).ljust(20) + 
                    ("Available= " + str(val['available'])).ljust(20) +
                    (val['availability_domain']).ljust(20)
                    )
                compartment_usage.append(val)
        return compartment_usage

    ##########################################################################
    # load_quotas
    ##########################################################################
    def load_quotas(self, quotas_client, compartments):
        quota_data = []

        # loop on all compartments
        for compartment in compartments:
            # skip Paas compartment
            if self.__if_managed_paas_compartment(compartment['name']):
                print(".", end="")
                continue

            quotas = []
            try:
                quotas = quotas_client.list_quotas(compartment['id'], lifecycle_state=oci.limits.models.QuotaSummary.LIFECYCLE_STATE_ACTIVE, sort_by="NAME").data
            except oci.exceptions.ServiceError as e:
                if 'go to your home region' in str(e):
                    #print("Service can only run at home region, skipping")
                    return
                if self.__check_service_error(e.code):
                    print(str(e.code))
                    self.__load_print_auth_warning()
                else:
                    raise

            print(".", end="")

            if quotas:

                # oci.limits.models.QuotaSummary
                for arr in quotas:
                    val = {
                        'id': str(arr.id),
                        'name': str(arr.name),
                        'description': str(arr.description),
                        'statements': [],
                        'time_created': str(arr.time_created),
                        'compartment_name': str(compartment['name']),
                        'compartment_id': str(compartment['id']),
                        'region_name': str(self.config['region']),
                        'defined_tags': [] if arr.defined_tags is None else arr.defined_tags,
                        'freeform_tags': [] if arr.freeform_tags is None else arr.freeform_tags,
                    }

                    # read quota statements
                    try:
                        quota = quotas_client.get_quota(arr.id).data
                        if quota:
                            val['statements'] = quota.statements
                    except oci.exceptions.ServiceError:
                        print ("Service Error")
                        print(oci.exceptions.ServiceError)
                        pass

                    # add the data
                    self.quota_data.append(val)


    ##########################################################################
    # Load compartments
    ##########################################################################
    def load_identity_compartments(self, identity):

        compartments = []

        try:
            # point to tenancy
            tenancy = self.data[self.C_IDENTITY][self.C_IDENTITY_TENANCY]

            # read all compartments to variable
            all_compartments = []
            try:
                all_compartments = oci.pagination.list_call_get_all_results(
                    identity.list_compartments,
                    tenancy['id'],
                    compartment_id_in_subtree=True
                ).data

            except oci.exceptions.ServiceError as e:
                if self.__check_service_error(e.code):
                    self.__load_print_auth_warning()
                else:
                    raise

            ###################################################
            # Build Compartments
            # return nested compartment list
            ###################################################
            def build_compartments_nested(identity_client, cid, path):
                try:
                    compartment_list = [item for item in all_compartments if str(item.compartment_id) == str(cid)]

                    if path != "":
                        path = path + " / "

                    for c in compartment_list:
                        if c.lifecycle_state == oci.identity.models.Compartment.LIFECYCLE_STATE_ACTIVE:                      
                            cvalue = {'id': str(c.id), 'name': str(c.name), 'path': path + str(c.name)}
                            compartments.append(cvalue)
                            build_compartments_nested(identity_client, c.id, cvalue['path'])

                except Exception as error:
                    raise Exception("Error in build_compartments_nested: " + str(error.args))

            ###################################################
            # Add root compartment
            ###################################################
            root_compartment = {'id': tenancy['id'], 'name': tenancy['name'] + " (root)", 'path': "/ " + tenancy['name'] + " (root)"}
            compartments.append(root_compartment)

            # Build the compartments
            build_compartments_nested(identity, tenancy['id'], "")

            # sort the compartment
            sorted_compartments = sorted(compartments, key=lambda k: k['path'])

            # if not filtered by compartment return
            self.data[self.C_IDENTITY][self.C_IDENTITY_COMPARTMENTS] = sorted_compartments

        except oci.exceptions.RequestException:
            raise
        except Exception as e:
            raise Exception("Error in __load_identity_compartments: " + str(e.args))

    ##########################################################################
    # Return lists
    ##########################################################################
    def get_limit_data(self):
        return self.limit_data

    def get_usage_data(self):
        return self.usage_data

    ##########################################################################
    # return tenancy data
    ##########################################################################
    def get_tenancy(self):
        return self.data[self.C_IDENTITY][self.C_IDENTITY_TENANCY]

    ##########################################################################
    # get tenancy id from file or override
    ##########################################################################
    def get_tenancy_id(self):
        return self.config["tenancy"]

    ##########################################################################
    # return compartment data
    ##########################################################################
    def get_compartment(self):
        return self.data[self.C_IDENTITY][self.C_IDENTITY_COMPARTMENTS]

    ##########################################################################
    # Build list of services within a region
    ##########################################################################
    def build_services_list(self, limits_client, tenancy_id):
        try:
            self.services = oci.pagination.list_call_get_all_results(limits_client.list_services, tenancy_id, sort_by="name").data
        
            for service in self.services:
                if str(service.name) not in self.service_list:
                    self.service_list.append(str(service.name))
        
        except oci.exceptions.ServiceError as e:
            print (str(e))
            if self.__check_service_error(e.code):
                self.__load_print_auth_warning("a", False)
            else:
                raise

    ##########################################################################
    # Exception catchers
    ##########################################################################
    def __load_print_auth_warning(self, special_char="a", increase_warning=True):
        if increase_warning:
            self.warning += 1
        print(special_char, end="")

    def __check_service_error(self, code):
        return 'max retries exceeded' in str(code).lower() or 'auth' in str(code).lower() or 'notfound' in str(code).lower() or code == 'Forbidden' or code == 'TooManyRequests' or code == 'IncorrectState' or code == 'LimitExceeded'

    ##########################################################################
    # check if managed paas compartment
    ##########################################################################
    def __if_managed_paas_compartment(self, name):
        return name == "ManagedCompartmentForPaaS"

    ##########################################################################
    # Main Menu
    ##########################################################################
    def main_menu(self):
        keep_running = 1
        
        tenancy = self.get_tenancy()
        compartments = self.get_compartment()
        all_compartments_usage = {}

        while keep_running:
            print ("\n")
            choice = input("Please choose an option:\n" +
                          "1. Tenancy Limit\n" +
                          "2. Quota Policies\n" +
                          "3. Compartment Usage\n" + 
                          "4. Quit\n" + 
                          "> "
                           )
            print ("\n")

            #if user picks 1, retrieve and/or display tenancy's limit
            if choice == '1':
                current_region = ''
                print("Start getting limits")
                then = datetime.datetime.now()

                #if the tenancy's limit has not been retrieved yet, retrieve them now
                if not self.limit_data:
                    for region_name in tenancy['list_region_subscriptions']:
                        #load region into data
                        self.load_oci_region_data(region_name)
                        #get tenancy limits
                        self.load_limits(self.limits_client, tenancy['id'])
               
                #time how long the retrieval takes
                now = datetime.datetime.now()
                print("Load limits time: " + str((now-then).total_seconds()) + " sec")   

                #display the tenancy's limits
                for things in self.limit_data:
                    if things['limit'] != 0:
                        if things['region_name'] != current_region:
                            current_region = things['region_name']
                            print ("\n")
                            print ("[Region: " + current_region + "]")

                        print (
                            (things['name'] + " ").ljust(20) +
                            (things['limit_name']).ljust(37) +
                            ("Limit= " + str(things['limit'])).ljust(20) +
                            ("Used= " + str(things['used'])).ljust(20) + 
                            ("Available= " + str(things['available'])).ljust(20) +
                            (things['availability_domain']).ljust(20)
                            )

            #If user picks 2, show quota policies
            elif choice == '2':
                print("Start getting quota policies")
                then = datetime.datetime.now()

                #if the quota policies have not been retrieved yet, retrieve them now
                if not self.quota_data:
                    for region_name in tenancy['list_region_subscriptions']:
                        # load region into data
                        self.load_oci_region_data(region_name)
                    
                        #Get quota policies
                        self.load_quotas(self.quotas_client, compartments)
                
                #time how long the retrieval takes
                now = datetime.datetime.now()
                print("Load quotas time: " + str((now-then).total_seconds()) + " sec")

                #display quota policies
                for policy in self.quota_data:
                    print ("Name: " + policy['name'] + "\n" +
                           "Compartment Name: " + policy['compartment_name'] + "\n" +
                           "Description : " + policy['description'] +  "\n" +
                           "Statements : ")
                    for statement in policy['statements']:
                        print ("    " + str(statement))

            ########################################################################################
            #If user picks 3, ask which compartment or all compartments
            elif choice == '3':
                stay_here = 1

                while stay_here:
                    choice = input("1. Usage of all compartments\n" +
                                   "2. Usage of a compartment\n" +
                                   "3. Go back\n"
                                   "> "
                                   )

                    #if the user chooses all compartments
                    if choice == '1':
                        stay_compartment = 1

                        #if the usages of all the compartments have not been retrieved yet, retrieve them now
                        if not self.usage_data:
                            for region_name in tenancy['list_region_subscriptions']:
                                # load region into data
                                self.load_oci_region_data(region_name)
                                for compartment in compartments:
                                        print (compartment)
                                        compartment_usage = self.load_compartment_usage(self.limits_client, compartment['id'], tenancy['id'])
                                        if compartment['id'] in self.usage_data:
                                            self.usage_data[compartment['id']] = self.usage_data[compartment['id']] + compartment_usage
                                        else:
                                            self.usage_data[compartment['id']] = compartment_usage

                        #ask which service the user would like to see the usages for
                        while stay_compartment:
                            service = input("Enter which service you would like to see (help to see valid commands): ")
                        
                            if service == 'help' or service =='?':
                                    print ("Valid options:")
                                    for service in self.service_list:
                                        print(service)
                                    print ("all to show all services")
                                    print ("q to go back\n")

                            #show all services in all the compartments
                            elif service == 'all':
                                current_region = ''
                                for compartment in compartments:
                                    print ("========================================")
                                    print ("Compartment: " + compartment['name'])
                                    print ("========================================")
                                    for things in self.usage_data[compartment['id']]:
                                            try:
                                                if things['limit'] > 0:
                                                    if things['region_name'] != current_region:
                                                        current_region = things['region_name']
                                                        print ("[Region: " + current_region + "]")
                                                    print (
                                                        (things['name'] + " ").ljust(20) +
                                                        (things['limit_name']).ljust(37) +
                                                        ("Used= " + str(things['used'])).ljust(20) + 
                                                        ("Available= " + str(things['available'])).ljust(20) +
                                                        (things['availability_domain']).ljust(20)
                                                        )
                                            except Exception as e:
                                                print ("\n")
                                                print("Crashed here: ")
                                                print (things)
                                                print (e)
                                                raise

                                    print("\n")

                            #show usage of a single service in all compartments
                            elif service in self.service_list:                 
                                current_region = ''
                                for compartment in compartments:
                                    print ("========================================")
                                    print ("Compartment: " + compartment['name'])
                                    print ("========================================")
                                    for things in self.usage_data[compartment['name']]:
                                            if things['limit'] > 0:
                                                if things['name'] == service:
                                                    if things['region_name'] != region_name:
                                                        current_region = things['region_name']
                                                        print ("[Region: " + current_region + "]")

                                                    print (
                                                        (things['name'] + " ").ljust(20) +
                                                        (things['limit_name']).ljust(37) +
                                                        ("Used= " + str(things['used'])).ljust(20) + 
                                                        ("Available= " + str(things['available'])).ljust(20) +
                                                        (things['availability_domain']).ljust(20)
                                                        )
                                                    printed = 1
                                print("\n")

                            #go back
                            elif service == 'q':
                                stay_compartment = 0
                                break

                            else:
                                print (service + " is not a valid service. Type help to see all valid services.")

                    #if the user chooses to the the usage in a single compartment
                    if choice == '2':
                        stay_compartment = 1
                        comp_name = ''
                        comp_id = ''
                        total_comp_usage = []

                        #ask which compartment the user is trying to get
                        chosen_comp = input("Enter a compartment's OCID or name: ")

                        #try to find the compartment
                        for compartment in compartments:
                            if chosen_comp == compartment['id']:
                                comp_id = chosen_comp
                                comp_name = compartment['name']
                                break
                            elif chosen_comp == compartment['name']:
                                comp_name = chosen_comp
                                comp_id = compartment['id']
                                break
                        if comp_id == '':
                            print ("Could not find compartment " + chosen_comp)
                            break

                        print("Start getting " + comp_name + " usages")
                        then = datetime.datetime.now()

                        print(compartment)
                        bInScope = True
                        for region_name in tenancy['list_region_subscriptions']:
                            #if "phoenix" in region_name or "ashburn" in region_name:
                            if self.bAllScope == False:
                                
                                # need to process in scope or not
                                bInScope = False
                                for scopeRegion in self.scope_list:
                                    if scopeRegion.strip() in region_name:
                                        bInScope = True
                                        break
                                 
                            if bInScope:   
                                print("Looking in: " + region_name)
                            
                                # load region into data
                                self.load_oci_region_data(region_name)
                            
                                # get compartment's usage
                                compartment_usage = self.load_compartment_usage(self.limits_client, comp_id, tenancy['id'])
                                total_comp_usage.append(compartment_usage)

                        now = datetime.datetime.now()
                        print("Load " + comp_name + " usage time: " + str((now-then).total_seconds()) + " sec")

                        while stay_compartment:
                            service = input("Enter which service you would like to see (help to see valid commands): ")
                        
                            if service == 'help' or service == '?':
                                    print ("Valid options:")
                                    for services in self.service_list:
                                        print(services)
                                    print ("all to show usage of all services")
                                    print ("print to write usages into an excel file")
                                    print ("q to go back\n")

                            #If user chooses 'all', list all usages in compartment that is >0
                            elif service == 'all':
                                current_region = ''
                                print (comp_name)
                                for each_usage in total_comp_usage:
                                    for things in each_usage:
                                        #if things['limit'] > 0:
                                        if things['used'] > 0:
                                            if things['region_name'] != current_region:
                                                current_region = things['region_name']
                                                print ("\n")
                                                print ("[Region: " + current_region + "]")

                                            print (
                                                (things['name'] + " ").ljust(20) +
                                                (things['limit_name']).ljust(37) +
                                                ("Used= " + str(things['used'])).ljust(20) + 
                                                ("Available= " + str(things['available'])).ljust(20) +
                                                (things['availability_domain']).ljust(20)
                                                )
                                print("\n")

                            #If user chooses a service, show usage of that service in compartment
                            elif service in self.service_list:          
                                printed = 0
                                current_region = ''
                                print (compartment['name'])
                                for each_usage in total_comp_usage:
                                    for things in each_usage:
                                        #if things['limit'] > 0:
                                        if things['used'] > 0:
                                            if things['name'] == service:
                                                if things['region_name'] != current_region:
                                                    print("Changing Region!")
                                                    current_region = things['region_name']
                                                    print ("\n")
                                                    print ("[Region: " + current_region + "]")
                                                print (
                                                    (things['name'] + " ").ljust(20) +
                                                    (things['limit_name']).ljust(37) +
                                                    ("Used= " + str(things['used'])).ljust(20) + 
                                                    ("Available= " + str(things['available'])).ljust(20) +
                                                    (things['availability_domain']).ljust(20)
                                                    )
                                                printed = 1

                                #the program could not find any of the searched service running in the compartment
                                if printed == 0:
                                    print ("This compartment does not have any " + service + " services running.\n")

                            #print the compartment usage
                            elif service == 'print':
                                print_usage(self.usage_location, total_comp_usage, self.path_separator)
                                print("Exported usages to an excel file to " + self.usage_location)

                            #choose another compartment
                            elif service == 'q':
                                stay_compartment = 0
                                break
                            
                            else:
                                print (service + " is not a valid service. Type help to see all valid services.\n")
                        pass

                    if choice == '3':
                        stay_here = 0

                    else:
                        print("That was not a valid option.")
            ########################################################################################

            #If user picks 4, quit
            elif choice == '4':
                keep_running = 0

            #If anything else, print error message and ask user to try again
            else:
                print ("That was not a valid option. Please try again.")