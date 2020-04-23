import oci

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

    limit_data = []
    quota_data = []


    warning = 0

    def __init__(self):
        self.config_file = oci.config.DEFAULT_LOCATION
        self.config_section = oci.config.DEFAULT_PROFILE
        self.create_signer(self.config_file, self.config_section)
        self.load_identity_main()
        tenancy = self.data[self.C_IDENTITY][self.C_IDENTITY_TENANCY]
        compartment = self.data[self.C_IDENTITY][self.C_IDENTITY_COMPARTMENTS]
        for region_name in tenancy['list_region_subscriptions']:
            # load region into data
            self.load_oci_region_data(region_name)

    ##########################################################################
    # Create signer
    ##########################################################################
    def create_signer(self, file, section):
        self.config = oci.config.from_file(file, section)
        self.signer = oci.signer.Signer(
            tenancy=self.config["tenancy"],
            user=self.config["user"],
            fingerprint=self.config["fingerprint"],
            private_key_file_location=self.config.get("key_file"),
            pass_phrase=oci.config.get_config_value_or_default(self.config, "pass_phrase"),
            private_key_content=self.config.get("key_content")
        )

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
            compartment_id = self.config["tenancy"]

            # Get and set the home region for the compartment. User crud operations need
            # to be performed in the home region.
            response = identity.list_region_subscriptions(compartment_id)
            for region in response.data:
                if region.is_home_region:
                    print (str(region.region_name))
                    identity.base_client.set_region(region.region_name)
                    break

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
            for es in sub_regions:
                data_subs.append(str(es.region_name))
                print (str(es.region_name))
                
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

    ##########################################################################
    # Load limits
    ##########################################################################
    def load_limits_main(self):
        find_compartment = 1

        limits_client = oci.limits.LimitsClient(self.config, signer=self.signer)
        quotas_client = oci.limits.QuotasClient(self.config, signer=self.signer)

        tenancy = self.get_tenancy()
        compartments = self.get_compartment()

        self.initialize_data_key(self.C_LIMITS, self.C_LIMITS_SERVICES)
        self.initialize_data_key(self.C_LIMITS, self.C_LIMITS_QUOTAS)

        limits = self.data[self.C_LIMITS]

        self.load_limits(limits_client, tenancy['id'])
        self.load_quotas(quotas_client, compartments)

        for thing in compartments:
            print(thing)
            self.load_compartment_limits(limits_client, thing['id'], tenancy['id'])


    
    ##########################################################################
    # load limits
    ##########################################################################
    def load_limits(self, limits_client, tenancy_id):        
        services = []
        try:
            services = oci.pagination.list_call_get_all_results(limits_client.list_services, tenancy_id, sort_by="name").data
        except oci.exceptions.ServiceError as e:
            print (str(e))
            if self.__check_service_error(e.code):
                self.__load_print_auth_warning("a", False)
            else:
                raise
        if services:

                # oci.limits.models.ServiceSummary
                for service in services:
                    print(".", end="")

                    # get the limits per service
                    limits = []
                    try:
                        limits = oci.pagination.list_call_get_all_results(limits_client.list_limit_values, tenancy_id, service_name=service.name, sort_by="name").data
                    except oci.exceptions.Exception as e:
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
                            'availability_domain': ("" if limit.availability_domain is None else str(limit.availability_domain)),
                            'scope_type': str(limit.scope_type),
                            'value': int(limit.value),
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
                            pass

                        # add to array
                        self.limit_data.append(val)
        
        """
        for things in self.limit_data:
            print ("{")
            print ("Region: " + things['region_name'])
            print ("Limit Name: " + things['limit_name'])
            print ("Limit: " + str(things['value']))
            if things['availability_domain'] != "":
                print ("Availability Domain: " + things['availability_domain'])
            print ("}\n")
        """

    ##########################################################################
    # load_quotas
    ##########################################################################
    def load_quotas(self, quotas_client, compartments):

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
                    print("Service can only run at home region, skipping")
                    return
                if self.__check_service_error(e.code):
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
                        pass

                    # add the data
                    self.quota_data.append(val)


                for things in self.quota_data:
                    print ("{")
                    print ("Name: " + things['name'])
                    print ("Compartment Name: " + things['compartment_name'])
                    print ("Description: " + things['description'])
                    print ("Statements: ")
                    for statement in things['statements']:
                        print ("   " + str(statement))
                    print ("}\n")



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
    # get compartment usages, limits, etc.
    ##########################################################################
    def load_compartment_limits(self, limits_client, compartment_id, tenancy_id):        
        services = []
        compartment_usage = []

        try:
            services = oci.pagination.list_call_get_all_results(limits_client.list_services, tenancy_id, sort_by="name").data
        except oci.exceptions.ServiceError as e:
            print (str(e))
            if self.__check_service_error(e.code):
                self.__load_print_auth_warning("a", False)
            else:
                raise
        if services:

                # oci.limits.models.ServiceSummary
                for service in services:
                    print(".", end="")

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
                            'value': int(limit.value),
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

                        compartment_usage.append(val)
                        
                    self.compartment_data[compartment_id] = compartment_usage

    def get_compartment_data(self):
        keep_printing = 1
        compartments = self.get_compartment()

        while keep_printing:
            #print a bunch of blank lines to seperate outputs

            #allow the user to choose which compartment they want to see via OCID or quite the program
            choice =  input("Enter an OCID (or q to quite): ")
            if choice == 'q':
                keep_printing = 0
            else:
                try:
                    for compartment in compartments:
                        if choice == compartment['id']:
                            print ("\n\n\n\n\n\n\n\n\n\n\n\n\n")
                            print ("----------------------------------------------------")
                            print ("You have chosen compartment: " + compartment['name'])
                            print ("----------------------------------------------------")

                    for things in self.compartment_data[choice]:
                        if things['available'] != 0:
                            if things['name'] == 'compute' or things['name'] == 'database':
                                print ("{")
                                print ("Region: " + things['region_name'])
                                print ("Name: " + things['name'])
                                if things['availability_domain'] != "":
                                    print ("Availability Domain: " + things['availability_domain'])
                                print ("Limit Name: " + things['limit_name'])
                                print ("Used: " + str(things['used']))
                                print ("Available: " + str(things['available']))
                                print ("}\n")

                    print ("----------------------------------------------------")
                    print ("You have chosen compartment: " + compartment['name'])
                    print ("----------------------------------------------------")

                except KeyError:
                    print("That was not a valid ID. Please try again.")
            print("\n")