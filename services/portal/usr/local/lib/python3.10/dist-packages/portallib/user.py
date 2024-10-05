import os
import json
import datetime
from typing import List, Dict
import logging
from urllib.parse import quote

import yaml
import pandas as pd
from tornado.httpclient import AsyncHTTPClient, HTTPRequest

from opensarlab.auth import encryptedjwt


class PortalUser:
    def __init__(self, username: str):
        self.username: str = username

        with open("/usr/local/secrets/portal-user-ro-token", "r") as f:
            self.portal_user_hub_ro_token: str = f.read()

        with open("/usr/local/secrets/portal-user-w-token", "r") as f:
            self.portal_user_hub_w_token: str = f.read()

        self.hub_api_url = os.environ.get(
            "JUPYTERHUB_API_URL", "http://127.0.0.1:8081/portal/hub/api"
        )

        self.log = logging.getLogger()

        # Get config lab info for page
        with open("/usr/local/etc/labs.yaml", "r") as f:
            self.lab_config: dict = yaml.load(f, Loader=yaml.FullLoader)

        self.lab_config_labs = self.lab_config.get("labs", [])

    async def update_user_geolocation_with_geolocation_api(
        self, ip_country_status: str, country_code: str, ip_address: str
    ) -> None:
        try:
            self.log.warning(
                f"Updating geolocation info for {self.username}: {ip_country_status}, {country_code}, {ip_address}"
            )
            geodata = {
                "username": self.username,
                "ip_country_status": ip_country_status,
                "country_code": country_code,
                "ip_address": ip_address,
            }
            data = encryptedjwt.encrypt(geodata)

            req = HTTPRequest(
                f"http://127.0.0.1/user/geolocation/update", body=data, method="POST"
            )

            response = await AsyncHTTPClient().fetch(req)
            if response.code != 200:
                raise Exception("Response returned with {response.code}")
        except Exception as e:
            self.log.error(
                f"Error in updating geolocation data for {self.username}: {e}"
            )

    async def get_latest_user_geolocation_from_geolocation_api(self) -> dict:
        try:
            response = await AsyncHTTPClient().fetch(
                f"http://127.0.0.1/user/geolocation/latest/username/{quote(self.username)}",
                method="GET",
            )
            if response.code == 200:
                data = encryptedjwt.decrypt(response.body)
            else:
                data = {}
        except Exception as e:
            self.log.error(f"Error in latest geolocation data for {self.username}: {e}")
            data = {}

        return data

    async def get_user_email_for_username(self, username: str) -> str:
        """
        From given username, get email address from Database. If no user or error, return ''.
        As a special case, username "osl-admin" will return the Admin email.
        """

        if not username:
            return ""

        try:
            url = f"http://127.0.0.1/portal/hub/native-user-info?username={quote(username)}"
            req = HTTPRequest(url)
            response = await AsyncHTTPClient().fetch(req)
            body = response.body.decode("utf8", "replace")
            user_info = dict(encryptedjwt.decrypt(body))
            user_info_error = user_info.get("error", None)
            if user_info_error:
                raise Exception(user_info_error)
            else:
                the_email = user_info.get("email", None)

        except Exception as e:
            logging.error(
                f"Something went wrong with getting user email info from username '{username}'... {e}"
            )
            the_email = None

        return the_email

    async def _get_mfa_status(self) -> bool:
        mfa_status = None
        try:
            url = f"http://127.0.0.1/portal/hub/native-user-info?username={quote(self.username)}"
            req = HTTPRequest(
                url,
                headers={"Authorization": f"token {self.portal_user_hub_ro_token}"},
            )
            response = await AsyncHTTPClient().fetch(req)
            body = response.body.decode("utf8", "replace")
            user_info = dict(encryptedjwt.decrypt(body))
            user_info_error = user_info.get("error", None)
            if user_info_error:
                raise Exception(user_info_error)
            else:
                mfa_status = user_info.get("has_2fa", None)
        except Exception as e:
            logging.error(
                f"Something went wrong with getting user MFA status from username '{self.username}'... {e}"
            )

        return mfa_status

    async def get_user_data_from_hub_api(self) -> dict:
        req = HTTPRequest(
            f"{self.hub_api_url}/users/{quote(self.username)}",
            headers={"Authorization": f"token {self.portal_user_hub_ro_token}"},
        )

        try:
            response = await AsyncHTTPClient().fetch(req)
            body = response.body.decode("utf8", "replace")
            json_body = json.loads(body)
            json_body["has_2fa"] = await self._get_mfa_status()
            return json_body
        except Exception as e:
            self.log.error(f"Portal_User: User Hub API: {e}")
            return {}

    async def get_user_profile_data_from_profile_api(self) -> Dict:
        """
        Get the user profile data for the user.
        """

        username = self.username

        try:
            response = await AsyncHTTPClient().fetch(
                f"http://127.0.0.1/user/profile/raw/{quote(username)}", method="GET"
            )
            if response.code == 200:
                data = encryptedjwt.decrypt(response.body)
            else:
                data = {}
        except Exception as e:
            self.log.error(f"Portal_user: Profile API: {e}")
            data = {}

        return data

    async def add_user_to_group(self, group: str) -> None:
        req = HTTPRequest(
            f"{self.hub_api_url}/groups/{quote(group)}/users",
            headers={"Authorization": f"token {self.portal_user_hub_w_token}"},
            body=json.dumps({"users": [str(self.username)]}),
            method="POST",
        )

        try:
            response = await AsyncHTTPClient().fetch(req)
            self.log.warning(f"User {self.username} added to group {group}")
            return response.code
        except Exception as e:
            self.log.error(f"Portal_user: add_user: {e}")

    async def remove_user_from_group(self, group: str) -> None:
        req = HTTPRequest(
            f"{self.hub_api_url}/groups/{quote(group)}/users",
            headers={"Authorization": f"token {self.portal_user_hub_w_token}"},
            body=json.dumps({"users": [str(self.username)]}),
            method="DELETE",
            allow_nonstandard_methods=True,
        )

        try:
            response = await AsyncHTTPClient().fetch(req)
            self.log.warning(f"User {self.username} removed from group {group}")
            return response.code
        except Exception as e:
            self.log.error(f"Portal_user: Remove User: {e}")

    def _consolidate_country_status(
        self, ip_country_status: dict, country_code: str
    ) -> str:
        effective_country_status = "unrestricted"
        if country_code in ip_country_status.get("limited", []):
            effective_country_status = "limited"
        if country_code in ip_country_status.get("prohibited", []):
            effective_country_status = "prohibited"

        return effective_country_status

    async def get_effective_lab_country_status_by_config(
        self, user_country_code: str
    ) -> dict:
        """
        From the ip_country_status config file, get the country code status for the user by lab.

        Portal status takes precendent.

                        | Portal
        Lab             | Unrestricted  | Limited       | Prohibited    |
        ----------------|------------------------------------------------
        Unrestricted    | Unrestricted  | Limited       | Prohibited    |
        Limited         | Limited       | Limited       | Prohibited    |
        Prohibited      | Prohibited    | Prohibited    | Prohibited    |

        """

        d = {
            "unrestricted": ["unrestricted", "limited", "prohibited"],
            "limited": ["limited", "limited", "prohibited"],
            "prohibited": ["prohibited", "prohibited", "prohibited"],
        }
        status_matrix = pd.DataFrame(data=d)
        status_matrix = status_matrix.rename(
            index={0: "unrestricted", 1: "limited", 2: "prohibited"}
        )

        portal_effective_country_status = self._consolidate_country_status(
            self.lab_config.get("ip_country_status", {}), user_country_code
        )

        # Cycle through labs
        total_effective_lab_statuses = {}
        for lab_config in self.lab_config_labs:

            lab_ip_country_status = self._consolidate_country_status(
                lab_config.get("ip_country_status", {}), user_country_code
            )
            effective_lab_status = status_matrix[lab_ip_country_status][
                portal_effective_country_status
            ]

            lab_name: str = lab_config.get("short_name")
            total_effective_lab_statuses[lab_name] = effective_lab_status

        return total_effective_lab_statuses

    async def _get_username_access_data(self, username: str) -> list:
        response = await AsyncHTTPClient().fetch(
            f"http://127.0.0.1/user/access/username/{quote(username)}",
            method="GET",
        )
        if response.code == 200:
            access_data = encryptedjwt.decrypt(response.body)
        else:
            access_data = []

        return access_data

    def _apply_compare_enabled_for_lab_and_config(
        self, row: pd.Series, config_lab_enabled: dict
    ) -> dict:
        """
        Used within a DataFrame Apply function.
        """
        access_lab_short_name: str = row.get("lab_short_name", "")

        is_config_lab_enabled: bool = config_lab_enabled.get(
            access_lab_short_name, False
        )

        # Maybe in the future each lab will have dynamic enabling via some other param
        # But for now, let's assume that access is always True.
        # Then we are only dependent on the config
        is_access_lab_enabled: bool = True

        row["enabled"] = (
            True if is_config_lab_enabled and is_access_lab_enabled else False
        )

        return row

    def _apply_lab_access_and_visibility(
        self, row: pd.Series, config_lab_accessibility: dict
    ) -> pd.DataFrame:
        """
        Used within a DataFrame Apply function.

        Whether an user can see the lab or access it depends on the user's country code status and the lab's level of access.
        There are three levels of lab access: public, protected, private.
        There are three levels of country code status: unrestricted, limited, prohibited. Prohibited cases are taken care of before this method.
        Usually, conditional access is granted when an username is explicitly given. Automatic access is given regardless if the username is given.
        Lab access can be of the values:
            1. deny - User access is prohibited. User never sees the lab card. This is normally handled by deleting the users entries in the access model.
            2. requested - User access is conditional. User always sees the lab card.
            3. automatic - User access is automatic. User always sees the lab card.
            4. special - User access is conditional. User only sees the lab card if access is granted.
        """

        d = {
            "unrestricted": ["automatic", "requested", "special"],
            "limited": ["requested", "requested", "special"],
        }

        status_matrix = pd.DataFrame(data=d)
        status_matrix = status_matrix.rename(
            index={0: "public", 1: "protected", 2: "private"}
        )

        lab_accessibility: str = config_lab_accessibility.get(
            row.lab_short_name, "private"
        )
        lab_country_status: str = str(row.lab_country_status)

        row["user_access_status"] = status_matrix[lab_country_status][lab_accessibility]

        return row

    def _apply_remove_expired_rows(self, row: pd.Series) -> str:
        """
        Used within a DataFrame Apply function.
        """
        if (
            not row.get("active_till_dates", None)
            or str(row.active_till_dates) == "None"
        ):
            return row

        else:

            active_till_dates = str(row.active_till_dates).split("=>")
            if len(active_till_dates) == 1:
                date1 = "1900-01-01"
                date2 = active_till_dates[0].replace('"', "").replace("'", "").strip()
            elif len(active_till_dates) == 2:
                date1 = active_till_dates[0].replace('"', "").replace("'", "").strip()
                date2 = active_till_dates[1].replace('"', "").replace("'", "").strip()
            else:
                self.log.error(
                    "More than one ' => ' found in Active Till Dates. Ignoring...."
                )
                return row

            try:
                if not date1:
                    date1 = "1900-01-01"
                date1 = datetime.datetime.fromisoformat(date1)
            except Exception as e:
                self.log.error(
                    f"Something went wrong with parsing Active Till Dates (date1): {e}. Ignoring..."
                )
                return row

            try:
                if not date2:
                    date2 = "2626-01-01"
                date2 = datetime.datetime.fromisoformat(date2)
            except Exception as e:
                self.log.error(
                    f"Something went wrong with parsing Active Till Dates (date2): {e}. Ignoring..."
                )
                return row

            if not date2.tzinfo:
                date2 = date2.astimezone(datetime.timezone.utc)

            if not date1.tzinfo:
                date1 = date1.astimezone(datetime.timezone.utc)

            if date1 > date2:
                self.log.error(
                    f"Date 1 ({date1}) is greater than Date 2 ({date2}). This is not possible. Ignoring..."
                )
                return row

            if date1 <= datetime.datetime.now(datetime.timezone.utc) <= date2:
                return row

            return row[0:0]

    def _apply_the_negated(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Used within a DataFrame Apply function.
        """
        #####
        # Remove negated usernames
        #####
        # Special use case: '!!' will negate all profiles in the lab and effectively deny access to everyone
        if [u for u in list(df.username) if str(u) == "!!"]:
            return df[0:0]

        # If '!*', then negate just any '*'
        # This would be useful if only access to defaults needs to be denied for everyone
        if [u for u in list(df.username) if str(u) == "!*"]:
            df.drop(df[df.username.isin(["!*", "*"])].index, inplace=True)

        # Any remaining !username will deny access for that user
        if [u for u in list(df.username) if str(u).startswith("!")]:
            return df[0:0]

        #####
        # Remove negated profiles
        #####
        exclaim_profiles = set(
            str(u) for u in list(df.lab_profiles) if str(u).startswith("!")
        )
        unexclaim_profiles = set(u.lstrip("!") for u in exclaim_profiles)
        delete_profiles = list(exclaim_profiles | unexclaim_profiles)

        df.drop(df[df.lab_profiles.isin(delete_profiles)].index, inplace=True)

        #####
        # Find final access status
        #####
        is_lab_access_automatic = (
            True if all(df.user_access_status == "automatic") else False
        )
        is_lab_access_requested = (
            True if all(df.user_access_status == "requested") else False
        )
        is_lab_access_special = (
            True if all(df.user_access_status == "special") else False
        )

        # If every username is a wildcard, then none are explicit usernames
        has_explicit_username = False if all(df.username == "*") else True

        if (
            is_lab_access_automatic
            or (is_lab_access_requested and has_explicit_username)
            or (is_lab_access_special and has_explicit_username)
        ):
            df["can_user_access_lab"] = True
        else:
            df["can_user_access_lab"] = False

        if (
            is_lab_access_automatic
            or is_lab_access_requested
            or (is_lab_access_special and has_explicit_username)
        ):
            df["can_user_see_lab_card"] = True
        else:
            df["can_user_see_lab_card"] = False

        df.drop(columns=["user_access_status"])

        #####
        # Remove rows without profiles, with duplicate profiles, or profiles are None
        # We are doing this here at the end after the usernames have been handled. If an explicit username has been given without any profiles, it is still valid.
        #####
        df.drop(df[df.lab_profiles.isin(["", "None", None])].index, inplace=True)
        df.drop_duplicates(subset="lab_profiles", keep="first", inplace=True)

        return df

    def _apply_consolidate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Used within a DataFrame Apply function.
        """

        return pd.Series(
            {
                "lab_profiles": df.lab_profiles.to_list(),
                "lab_country_status": df.lab_country_status.to_list().pop(),
                "can_user_access_lab": df.can_user_access_lab.to_list().pop(),
                "can_user_see_lab_card": df.can_user_see_lab_card.to_list().pop(),
                "time_quota": None,
            }
        )

    async def get_user_data_from_access_api(self, country_code: str) -> list:
        """
        Take User Access info from Access DB and parse info about user.

        params: country_code. The user's current country code.

        return: A dict containing user access info by lab.

            {
                '{lab_short_name}': {
                    'lab_profiles': list[str],
                    'time_quota': None,
                    'lab_accessibility': 'unrestricted' || 'limited',
                    'can_user_access_lab': bool,
                    'can_user_see_lab_card': bool,
                },
            }

        """

        username = self.username
        access_data = []

        #####
        # Get access data
        #####
        try:
            access_data.extend(await self._get_username_access_data(f"{username}"))
            access_data.extend(await self._get_username_access_data(f"!{username}"))
            access_data.extend(await self._get_username_access_data("*"))
            access_data.extend(await self._get_username_access_data("!*"))
            access_data.extend(await self._get_username_access_data("!!"))

        except Exception as e:
            self.log.error(f"Portal_user: Access API: {e}")
            access_data = []

        df_access_data = pd.DataFrame(access_data)

        if df_access_data.empty:
            return {}

        #####
        # Remove unneeded columns
        #####
        df_access_data.drop(
            ["time_quota", "comments", "row_id"], axis=1, inplace=True, errors="ignore"
        )

        #####
        # Remove whitespace from all elements
        #####
        df_access_data = df_access_data.map(lambda x: str(x).strip())

        #####
        # If access lab name is not also found in the portal config, remove lab name from access df
        #####
        config_lab_short_names = [lab.get("short_name") for lab in self.lab_config_labs]
        df_access_data = df_access_data[
            df_access_data.lab_short_name.isin(config_lab_short_names)
        ]

        if df_access_data.empty:
            return {}

        #####
        # If lab is not enabled in portal config, remove lab name from access df
        #####
        config_lab_enabled: dict = {
            lab.get("short_name"): lab.get("enabled", True)
            for lab in self.lab_config_labs
        }

        df_access_data = df_access_data.apply(
            self._apply_compare_enabled_for_lab_and_config,
            config_lab_enabled=config_lab_enabled,
            axis=1,
        )
        df_access_data = df_access_data[df_access_data.enabled == True].reset_index(
            drop=True
        )

        # We don't need the 'enabled' field anymore
        df_access_data.drop(["enabled"], axis=1, inplace=True, errors="ignore")

        #####
        # Get effective lab country status
        #####
        effective_lab_country_status_by_config: dict = (
            await self.get_effective_lab_country_status_by_config(country_code)
        )
        df_access_data["lab_country_status"] = df_access_data.lab_short_name.map(
            lambda lab_name: effective_lab_country_status_by_config.get(
                lab_name, "unknown"
            )
        )

        #####
        # Remove prohibited
        #####
        df_access_data.drop(
            df_access_data[
                df_access_data.lab_country_status.isin(["prohibited", "unknown"])
            ].index,
            inplace=True,
        )

        #####
        # Get default effective accessibility per lab
        #####
        config_lab_accessibility: dict = {
            lab.get("short_name"): lab.get("accessibility", "private")
            for lab in self.lab_config_labs
        }
        df_access_data = df_access_data.apply(
            self._apply_lab_access_and_visibility,
            config_lab_accessibility=config_lab_accessibility,
            axis=1,
        )

        #####
        #  Remove expired profiles
        #####
        df_access_data = df_access_data.apply(
            self._apply_remove_expired_rows, axis=1
        ).reset_index(drop=True)

        # We don't need the active_till_dates field anymore
        df_access_data.drop(
            ["active_till_dates"], axis=1, inplace=True, errors="ignore"
        )

        if df_access_data.empty:
            return {}

        #####
        # Split up profiles that are seperated by commas into their own rows
        #####
        df_access_data["lab_profiles"] = df_access_data.lab_profiles.map(
            lambda e: str(e).split(",")
        )
        df_access_data = df_access_data.explode("lab_profiles").reset_index(drop=True)

        # Remove whitespace from all profiles
        df_access_data.lab_profiles = df_access_data.lab_profiles.map(
            lambda x: str(x).strip()
        )

        #####
        # Remove negated
        #####
        df_access_data = (
            df_access_data.groupby(["lab_short_name"])
            .apply(self._apply_the_negated)
            .reset_index(drop=True)
        )

        #####
        # Consolidate info for Access object
        #####
        access = df_access_data.groupby(["lab_short_name"]).apply(
            self._apply_consolidate
        )
        access = access.to_dict("index")

        return access
