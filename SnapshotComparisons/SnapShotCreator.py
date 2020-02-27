import oci

class oci_limits(object):

    # Identity Identifiers
    C_IDENTITY = 'identity'
    C_IDENTITY_TENANCY = 'tenancy'
    C_IDENTITY_COMPARTMENTS = 'compartments'

    # limits
    C_LIMITS = "limits"
    C_LIMITS_SERVICES = "services"
    C_LIMITS_QUOTAS = "quotas"

    def __init__(self):
        self.config = oci.config.DEFAULT_LOCATION
        self.config_default = oci.config.DEFAULT_PROFILE

        self.signer = generate_signer_from_config(self.config, self.config_default)

    def generate_signer_from_config(self, config_file, config_section):
            # create signer from config for authentication
            # pass in oci.config.DEFAULT_LOCATION, oci.config.DEFAULT_PROFILE as arguments

            self.config = oci.config.from_file(config_file, config_section)
            self.signer = oci.signer.Signer(
                tenancy=self.config["tenancy"],
                user=self.config["user"],
                fingerprint=self.config["fingerprint"],
                private_key_file_location=self.config.get("key_file"),
                pass_phrase=oci.config.get_config_value_or_default(self.config, "pass_phrase"),
                private_key_content=self.config.get("key_content")
            )

    # return tenancy data
    def get_tenancy(self):
        return self.data[self.C_IDENTITY][self.C_IDENTITY_TENANCY]

    # return compartment data
    def get_compartment(self):
        return self.data[self.C_IDENTITY][self.C_IDENTITY_COMPARTMENTS]

    # initialize data key if not exist
    def __initialize_data_key(self, module, section):
        if module not in self.data:
            self.data[module] = {}
        if section not in self.data[module]:
            self.data[module][section] = []

    # __load_limits_main
    def __load_limits_main(self):
        try:
            print("Limits and Quotas...")

            # LimitsClient
            limits_client = oci.limits.LimitsClient(self.config, signer=self.signer)

            # QuotasClient
            quotas_client = oci.limits.QuotasClient(self.config, signer=self.signer)

            # reference to tenancy
            tenancy = self.get_tenancy()

            # reference to compartments
            compartments = self.get_compartment()

            # add the key if not exists
            self.__initialize_data_key(self.C_LIMITS, self.C_LIMITS_SERVICES)
            self.__initialize_data_key(self.C_LIMITS, self.C_LIMITS_QUOTAS)

            # reference to limits
            limits = self.data[self.C_LIMITS]

            # append the data
            limits[self.C_LIMITS_SERVICES] += self.__load_limits(limits_client, tenancy['id'])
            limits[self.C_LIMITS_QUOTAS] += self.__load_quotas(quotas_client, compartments)
            print("")

        except oci.exceptions.RequestException:
            raise
        except oci.exceptions.ServiceError:
            raise
        except Exception as e:
            self.__print_error("__load_limits_main", e)

    # __load_limits
    def __load_limits(self, limits_client, tenancy_id):
        data = []
        cnt = 0
        start_time = time.time()

        try:
            self.__load_print_status("Limits")

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
                            'value': str(limit.value),
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
                        cnt += 1
                        data.append(val)

            self.__load_print_cnt(cnt, start_time)
            return data

        except oci.exceptions.RequestException as e:
            if self.__check_request_error(e):
                return data
            raise
        except Exception as e:
            self.__print_error("__load_limits", e)
            return data

    ##########################################################################
    # __load_quotas
    ##########################################################################
    def __load_quotas(self, quotas_client, compartments):
        data = []
        cnt = 0
        start_time = time.time()

        try:
            self.__load_print_status("Quotas")

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
                        return data
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
                        cnt += 1
                        data.append(val)

            self.__load_print_cnt(cnt, start_time)
            return data

        except oci.exceptions.RequestException as e:
            if self.__check_request_error(e):
                return data
            raise
        except Exception as e:
            self.__print_error("__load_quotas", e)
            return data
pass