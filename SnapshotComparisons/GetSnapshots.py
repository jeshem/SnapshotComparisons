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
    number_of_regions = 0

    limit_data = []

    def __init__(self):
        self.config_file = oci.config.DEFAULT_LOCATION
        self.config_section = oci.config.DEFAULT_PROFILE
        self.create_signer(self.config_file, self.config_section)
        self.load_identity_main()
        tenancy = self.data[self.C_IDENTITY][self.C_IDENTITY_TENANCY]
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

            # get tenancy id from the config file
            tenancy_id = self.get_tenancy_id()
            self.data[self.C_IDENTITY] = {}

            self.load_identity_tenancy(identity, tenancy_id)

        except oci.exceptions.RequestException:
            raise
        except oci.exceptions.ServiceError:
            raise
        except Exception as e:
            self.__print_error("__load_identity_main: ", e)


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

            data_subs = ['eu-frankfurt-1',
                         'us-phoenix-1',
                         'us-ashburn-1']
            #for es in sub_regions:
                #data_subs = [str(es.region_name)]
                #self.number_of_regions += 1
            

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

    def get_tenancy(self):
        return self.data[self.C_IDENTITY][self.C_IDENTITY_TENANCY]

    def get_tenancy_id(self):
        return self.config["tenancy"]


    ##########################################################################
    # Load limits
    ##########################################################################
    def load_limits_main(self):
        limits_client = oci.limits.LimitsClient(self.config, signer=self.signer)
        tenancy = self.get_tenancy()
        self.initialize_data_key(self.C_LIMITS, self.C_LIMITS_SERVICES)
        limits = self.data[self.C_LIMITS]

        #limits[self.C_LIMITS_SERVICES] += self.load_limits(limits_client, tenancy['id'])

        self.get_limit(limits_client, tenancy['id'])

    
    ##########################################################################
    # get limits
    ##########################################################################
    def get_limit(self, limits_client, tenancy_id):        
        services = []
        try:
            services = oci.pagination.list_call_get_all_results(limits_client.list_services, tenancy_id, sort_by="name").data
        except oci.exceptions.ServiceError as e:
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
                            'used': "",
                            'available': "",
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
                                val['used'] = str(usage.used)
                            if usage.available:
                                val['available'] = str(usage.available)
                        except Exception:
                            pass

                        # add to array
                        self.limit_data.append(val)
        
        for things in self.limit_data:
            print ("{")
            print ("Region: " + things['region_name'])
            print ("Limit Name: " + things['limit_name'])
            print ("Limit: " + str(things['value']))
            if things['availability_domain'] != "":
                print ("Availability Domain: " + things['availability_domain'])
            print ("}\n")


    ##########################################################################
    # Return lists
    ##########################################################################
    def get_data_list(self):
        return self.limit_data


    ##########################################################################
    # Exception catchers
    ##########################################################################
    def __load_print_auth_warning(self, special_char="a", increase_warning=True):
        if increase_warning:
            self.warning += 1
        print(special_char, end="")

    def __check_service_error(self, code):
        return 'max retries exceeded' in str(code).lower() or 'auth' in str(code).lower() or 'notfound' in str(code).lower() or code == 'Forbidden' or code == 'TooManyRequests' or code == 'IncorrectState' or code == 'LimitExceeded'

