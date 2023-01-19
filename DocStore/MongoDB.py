import time
from typing import Optional
from pymongo import MongoClient
from dotenv import load_dotenv
import FFLogs.API

load_dotenv()


class MongoDBConnection:
    def __init__(self, uri: str, certificate_file: str, allow_updates_every_n_seconds: int) -> None:
        """
        :param uri: The URI to connect to the MongoDB database.
        :param certificate_file: The path to the certificate file.
        :param allow_updates_every_n_seconds: The minimum time between updates to a report from the FFLogs API.
        """
        # host=os.getenv("MONGODB_URI"), tls=True, tlsCertificateKeyFile=os.getenv("MONGODB_CERT")
        # Connect to the corresponding MongoDB database and prepare the collections.
        self.__client = MongoClient(host=uri, tls=True, tlsCertificateKeyFile=certificate_file)
        self.__db = self.__client.VodSync
        self.__auth_collection = self.__db.auths
        self.__report_collection = self.__db.reports
        self.__metadata_collection = self.__db.metadata
        # Prepare metadata (FFLogs Encounter Name Mapping) if it doesn't exist.
        self.__fflogs_encounters = self.__metadata_collection.find_one({"name": "encounter_dict"})
        if not self.__fflogs_encounters:
            self.__metadata_collection.insert_one({"name": "encounter_dict",
                                                  "encounter_mappings": {"0": "Undefined Zone"}})
            self.__fflogs_encounters = self.__metadata_collection.find_one(
                {"name": "encounter_dict"})["encounter_mappings"]
        else:
            self.__fflogs_encounters = self.__fflogs_encounters["encounter_mappings"]
        # Store the minimum time between updates to a report.
        self.__allow_updates_every_n_seconds = allow_updates_every_n_seconds

    def store_auth_keys(self, username: str, auths: dict) -> None:
        """
        Inserts or updates an auths document for given user(name).
        :param username: The user to store the auth document for.
        :param auths: The known auths for the user.
        """
        auths["user"] = username
        if "_id" in auths:
            self.__auth_collection.replace_one({"_id": auths["_id"]}, auths, upsert=True)
        else:
            self.__auth_collection.insert_one(auths)

    def get_auth_keys(self, username: str) -> dict:
        """
        Returns stored authentication keys for given user key (email)
        :param username: The e-mail of the user
        :return: Auth keys stored for this user. An empty dictionary if none exists.
        """
        auth = self.__auth_collection.find_one({"user": username})
        if not auth:
            return dict()
        else:
            return auth

    def find_or_load_report(self, code: str, fflogs_token: str, update: bool = False, unknown: bool = False) -> (
            int, Optional[dict]):
        """
        Attempt to find a report by code. If it doesn't exist, make one attempt to load it from FFLogs using the
        provided auth token.
        :param code: The report code.
        :param fflogs_token: The fflogs auth token.
        :param update: If True, try to refresh the log if it is found in the database.
        If this fails, return the old report.
        :param unknown: Whether to include unknown encounters (ID=0). Only when the log is updated from the database.
        :return: A status code for the request, and the report data if it could be found or loaded. Otherwise, the
        report may be None or incomplete and should not be used.
        """
        report = self.__report_collection.find_one({"code": code})
        status = 200
        if not report:
            # Attempt to load the report from FFLogs.
            status, report = FFLogs.API.get_report_data(fflogs_token, code)
            if status == 200:
                if report is not None:
                    # If the report was loaded successfully, store it in the database.
                    self.__report_collection.insert_one(report)
                else:
                    # Custom error code to signify that the report is successfully loaded, but has no data.
                    # Note that this is different from an empty report, as here, no metadata is available.
                    status = 800
        else:
            # If the report was found in the database, check if it needs to be updated.
            if update and time.time() - report["loaded_at"] > self.__allow_updates_every_n_seconds:
                status, new_report = FFLogs.API.try_update_report(fflogs_token, report, unknown=unknown)
                if status == 200:
                    # If the report was updated successfully, store the new report in the database.
                    new_report["_id"] = report["_id"]
                    self.__report_collection.replace_one({"_id": report["_id"]}, new_report, upsert=True)
                    # Return the new report in this case.
                    report = new_report

        if report:
            # Try to append encounter names.
            status, report = self.__append_encounter_dict(report, fflogs_token)

            # We don't return the ID of the report in responses.
            if "_id" in report:
                del report["_id"]

        # Return whatever latest status code and report we have as the final result.
        return status, report

    def __append_encounter_dict(self, report: dict, fflogs_token: str) -> (int, Optional[dict]):
        """
        Appends the encounter dictionary for the encounter ID of all fights provided in the report to it.
        :param report: The report to append the encounter dictionary to.
        :param fflogs_token: The fflogs auth token.
        :return: The status code and the report. If the status is 200, this function guarantees
        all non-zero encounter IDs within fights resolve to a name. Otherwise, the report is unmodified from the input.
        """
        status = 200
        required_id_set = set([fight["encounterID"] for fight in report["fights"]])
        for encounter_id in required_id_set:
            # The encounter dictionary uses strings due to MongoDB limitations.
            if str(encounter_id) not in self.__fflogs_encounters:
                # Try to query each missing encounter ID from FFLogs.
                status, name = FFLogs.API.query_for_encounter_name(fflogs_token, encounter_id)
                if status == 200:
                    # If the name was found, store it in the dictionary and the database.
                    # This is not very performant, but it is a one-time cost, and ensures that if we fail partway
                    # through the process, we don't have to start over.
                    self.__fflogs_encounters[str(encounter_id)] = name
                    self.__metadata_collection.replace_one({"name": "encounter_dict"},
                                                           {"name": "encounter_dict",
                                                            "encounter_mappings": self.__fflogs_encounters},
                                                           upsert=True)
                else:
                    # We stop on a non-200 status code.
                    break
        # If we succeeded, append the dictionary to the report.
        if status == 200:
            report["encounternames"] = {int(k): v for k, v in self.__fflogs_encounters.items()
                                        if int(k) in required_id_set}

        return status, report

    def get_client(self) -> MongoClient:
        """
        Returns the underlying MongoClient.
        :return: The underlying MongoClient.
        """
        return self.__client
