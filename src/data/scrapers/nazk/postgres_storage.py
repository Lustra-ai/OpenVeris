"""PostgreSQL storage for NAZK declarations with full data parsing."""

import json
from decimal import Decimal, InvalidOperation
from typing import Any

import psycopg2
import psycopg2.extras

from src.utils.logger import init_logger


class PostgreSQLStorage:
    """PostgreSQL storage for NAZK declarations with comprehensive data parsing."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "openveris",
        user: str = "openveris",
        password: str = "openveris_dev_password",
    ):
        """Initialize PostgreSQL storage.

        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            database: Database name
            user: Database user
            password: Database password
        """
        self.logger = init_logger(__name__)
        self.connection_params = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password,
        }
        self._test_connection()

    def _test_connection(self):
        """Test database connection."""
        try:
            conn = psycopg2.connect(**self.connection_params)  # type: ignore[call-overload]
            conn.close()
            self.logger.info("PostgreSQL connection successful")
        except Exception as e:
            self.logger.error(f"PostgreSQL connection failed: {e}")
            raise

    def _get_connection(self):
        """Get a new database connection."""
        return psycopg2.connect(**self.connection_params)  # type: ignore[call-overload]

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    @staticmethod
    def _safe_str(value: Any, default: str | None = None) -> str | None:
        """Get string value, handling masked/confidential data."""
        if not value or value == "[Конфіденційна інформація]" or value == "[Не застосовується]":
            return default
        return str(value).strip() if value else default

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        """Get integer value safely."""
        if not value or value == "[Конфіденційна інформація]":
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_decimal(value: Any) -> Decimal | None:
        """Get decimal value, handling Ukrainian format (comma as decimal separator)."""
        if not value or value == "[Конфіденційна інформація]":
            return None
        try:
            # Handle Ukrainian number format: "29,3" → 29.3
            str_value = str(value).replace(",", ".").replace(" ", "")
            return Decimal(str_value)
        except (ValueError, TypeError, InvalidOperation):
            return None

    @staticmethod
    def _safe_date(value: Any) -> str | None:
        """Parse date string to ISO format."""
        if not value:
            return None

        str_value = str(value).strip()

        # Handle all types of masked data (anything in square brackets)
        if str_value.startswith("[") and str_value.endswith("]"):
            return None

        try:
            # Handle format: "28.07.2016" → "2016-07-28"
            if "." in str_value:
                parts = str_value.split(".")
                if len(parts) == 3:
                    day, month, year = parts
                    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            return str_value
        except Exception:
            return None

    @staticmethod
    def _extract_declaration_year(step_0: dict) -> int | None:
        """Extract declaration year from various possible fields."""
        # Try direct declarationYear field (camelCase)
        year = step_0.get("declarationYear")
        if year:
            year_int = PostgreSQLStorage._safe_int(year)
            if year_int:
                return year_int

        # Try declaration_year field (snake_case)
        year = step_0.get("declaration_year")
        if year:
            year_int = PostgreSQLStorage._safe_int(year)
            if year_int:
                return year_int

        # Try changesYear field (for correction declarations)
        year = step_0.get("changesYear")
        if year:
            year_int = PostgreSQLStorage._safe_int(year)
            if year_int:
                return year_int

        # Try type-specific fields (declarationYear1, declarationYear2, declarationYear3, declarationYear4, etc.)
        # Try both camelCase and snake_case
        declaration_type = step_0.get("declarationType") or step_0.get("declaration_type")
        if declaration_type:
            type_specific_field = f"declarationYear{declaration_type}"
            year = step_0.get(type_specific_field)
            if year:
                year_int = PostgreSQLStorage._safe_int(year)
                if year_int:
                    return year_int

        # Try extracting from declarationYearTo (format: "31.12.2024")
        year_to = step_0.get("declarationYearTo")
        if year_to and isinstance(year_to, str) and "." in year_to:
            parts = year_to.split(".")
            if len(parts) == 3:
                year_int = PostgreSQLStorage._safe_int(parts[-1])
                if year_int:
                    return year_int

        # Try extracting from declarationYearFrom
        year_from = step_0.get("declarationYearFrom")
        if year_from and isinstance(year_from, str) and "." in year_from:
            parts = year_from.split(".")
            if len(parts) == 3:
                year_int = PostgreSQLStorage._safe_int(parts[-1])
                if year_int:
                    return year_int

        # Default to None (will cause error, but we can't guess)
        return None

    # ========================================================================
    # DECLARANT MANAGEMENT
    # ========================================================================

    def _upsert_declarant(self, step_1_data: dict, cursor) -> str:
        """Find or create declarant, return UUID.

        Args:
            step_1_data: Declaration step_1 data with personal info
            cursor: Database cursor

        Returns:
            Declarant UUID
        """
        lastname = self._safe_str(step_1_data.get("lastname"))
        firstname = self._safe_str(step_1_data.get("firstname"))
        middlename = self._safe_str(step_1_data.get("middlename"))
        tax_number = self._safe_str(step_1_data.get("taxNumber"))
        unzr = self._safe_str(step_1_data.get("unzr"))

        # Try to find existing declarant
        if tax_number and tax_number != "[Конфіденційна інформація]":
            cursor.execute("SELECT id FROM declarants WHERE tax_number = %s LIMIT 1", (tax_number,))
            result = cursor.fetchone()
            if result:
                return result[0]  # type: ignore[no-any-return]

        # Try by UNZR
        if unzr and unzr != "[Конфіденційна інформація]":
            cursor.execute("SELECT id FROM declarants WHERE unzr = %s LIMIT 1", (unzr,))
            result = cursor.fetchone()
            if result:
                return result[0]  # type: ignore[no-any-return]

        # Try by full name
        cursor.execute(
            """SELECT id FROM declarants
               WHERE UPPER(lastname) = UPPER(%s)
               AND UPPER(firstname) = UPPER(%s)
               AND UPPER(COALESCE(middlename, '')) = UPPER(COALESCE(%s, ''))
               LIMIT 1""",
            (lastname, firstname, middlename),
        )
        result = cursor.fetchone()
        if result:
            return result[0]  # type: ignore[no-any-return]

        # Create new declarant
        cursor.execute(
            """INSERT INTO declarants (
                tax_number, unzr, lastname, firstname, middlename,
                changed_name, first_seen_at, last_updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id""",
            (
                tax_number,
                unzr,
                lastname,
                firstname,
                middlename,
                step_1_data.get("changedName") == "1",
            ),
        )
        result = cursor.fetchone()
        if result:
            declarant_id = result[0]
            self.logger.info(f"Created new declarant: {lastname} {firstname}")
            return declarant_id  # type: ignore[no-any-return]
        raise ValueError("Failed to create declarant: no ID returned")

    # ========================================================================
    # DECLARATION SAVE
    # ========================================================================

    def save_declaration(self, document_id: str, raw_data: dict) -> bool:
        """Save complete declaration with all related data.

        Args:
            document_id: NAZK document ID
            raw_data: Complete declaration data from API

        Returns:
            True if saved successfully
        """
        try:
            # Validate raw_data is a dict
            if not isinstance(raw_data, dict):
                self.logger.warning(
                    f"Skipping declaration {document_id}: API returned non-dict response: {type(raw_data).__name__}"
                )
                return False

            with self._get_connection() as conn, conn.cursor() as cursor:
                # Extract steps
                data_section = raw_data.get("data", {})
                step_0 = data_section.get("step_0", {}).get("data", {})
                step_1 = data_section.get("step_1", {}).get("data", {})
                step_2 = data_section.get("step_2", {}).get("data", [])
                step_3 = data_section.get("step_3", {}).get("data", [])
                step_4 = data_section.get("step_4", {}).get("data", [])
                step_5 = data_section.get("step_5", {}).get("data", [])
                step_6 = data_section.get("step_6", {}).get("data", [])
                step_7 = data_section.get("step_7", {}).get("data", [])
                step_8 = data_section.get("step_8", {}).get("data", [])
                step_9 = data_section.get("step_9", {}).get("data", [])
                step_10 = data_section.get("step_10", {}).get("data", [])
                step_11 = data_section.get("step_11", {}).get("data", [])
                step_13 = data_section.get("step_13", {}).get("data", [])
                step_17 = data_section.get("step_17", {}).get("data", [])

                # 1. Upsert declarant
                declarant_id = self._upsert_declarant(step_1, cursor)

                # 2. Insert declaration
                declaration_id = self._insert_declaration(
                    document_id,
                    declarant_id,
                    step_0,
                    step_1,
                    json.dumps(raw_data, ensure_ascii=False),
                    cursor,
                )

                # 3. Insert family members
                family_member_ids = self._save_family_members(declaration_id, step_2, cursor)

                # 4. Insert real estate
                self._save_real_estate(declaration_id, step_3, family_member_ids, cursor)

                # 5. Insert valuables
                if step_4:
                    self._save_valuables(declaration_id, step_4, family_member_ids, cursor)

                # 6. Insert memberships
                if step_5:
                    self._save_memberships(declaration_id, step_5, family_member_ids, cursor)

                # 7. Insert vehicles
                if step_6:
                    self._save_vehicles(declaration_id, step_6, family_member_ids, cursor)

                # 8. Insert securities
                if step_7:
                    self._save_securities(declaration_id, step_7, family_member_ids, cursor)

                # 9. Insert corporate rights
                if step_8:
                    self._save_corporate_rights(declaration_id, step_8, family_member_ids, cursor)

                # 10. Insert intangible assets
                if step_9:
                    self._save_intangible_assets(declaration_id, step_9, family_member_ids, cursor)

                # 11. Insert expenses
                if step_10:
                    self._save_expenses(declaration_id, step_10, family_member_ids, cursor)

                # 12. Insert income sources
                self._save_income_sources(declaration_id, step_11, family_member_ids, cursor)

                # 13. Insert liabilities
                if step_13:
                    self._save_liabilities(declaration_id, step_13, family_member_ids, cursor)

                # 14. Insert bank accounts
                if step_17:
                    self._save_bank_accounts(declaration_id, step_17, family_member_ids, cursor)

                conn.commit()
                self.logger.info(f"Saved declaration {document_id}")
                return True

        except Exception as e:
            self.logger.error(f"Error saving declaration {document_id}: {e}", exc_info=True)
            return False

    def _insert_declaration(
        self, document_id: str, declarant_id: str, step_0: dict, step_1: dict, raw_json: str, cursor
    ) -> str:
        """Insert declaration record."""
        cursor.execute(
            """INSERT INTO declarations (
                declarant_id, document_id, declaration_type, declaration_year,
                reporting_period_from, reporting_period_to, submitted_at,
                work_place, work_place_edrpou, work_post, post_type, post_category,
                responsible_position, public_person, corruption_affected,
                country_id, region, district, community, city, city_type,
                street, house_num, apartments_num, post_code,
                same_reg_living_address, raw_data, scraped_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW()
            )
            ON CONFLICT (document_id) DO UPDATE SET
                updated_at = NOW(),
                raw_data = EXCLUDED.raw_data,
                submitted_at = EXCLUDED.submitted_at
            RETURNING id""",
            (
                declarant_id,
                document_id,
                self._safe_int(step_0.get("declarationType")),
                self._extract_declaration_year(step_0),
                self._safe_date(step_0.get("declarationYearFrom")),
                self._safe_date(step_0.get("declarationYearTo")),
                self._safe_date(step_0.get("introDate")),
                self._safe_str(step_1.get("workPlace")),
                self._safe_str(step_1.get("workPlaceEdrpou")),
                self._safe_str(step_1.get("workPost")),
                self._safe_str(step_1.get("postType")),
                self._safe_str(step_1.get("postCategory")),
                step_1.get("responsiblePosition") == "Так",
                step_1.get("public_person") == "Так",
                step_1.get("corruptionAffected") == "Так",
                self._safe_int(step_1.get("country")),
                self._safe_str(step_1.get("region")),
                self._safe_str(step_1.get("district")),
                self._safe_str(step_1.get("community")),
                self._safe_str(step_1.get("city")),
                self._safe_str(step_1.get("cityType")),
                self._safe_str(step_1.get("street")),
                self._safe_str(step_1.get("houseNum")),
                self._safe_str(step_1.get("apartmentsNum")),
                self._safe_str(step_1.get("postCode")),
                step_1.get("sameRegLivingAddress") == "1",
                raw_json,
            ),
        )
        result = cursor.fetchone()
        if result:
            return result[0]  # type: ignore[no-any-return]
        raise ValueError(f"Failed to insert declaration {document_id}: no ID returned")

    # ========================================================================
    # FAMILY MEMBERS
    # ========================================================================

    def _save_family_members(
        self, declaration_id: str, step_2_data: list[dict], cursor
    ) -> dict[str, str]:
        """Save family members and return mapping of internal ID to UUID.

        Also links family members to declarants table if they are also public officials
        to avoid person duplication.
        """
        family_member_ids = {}

        for member in step_2_data:
            # Check if this family member is also a declarant
            declarant_id = None
            tax_number = self._safe_str(member.get("taxNumber"))
            unzr = self._safe_str(member.get("unzr"))

            # Try to find matching declarant by tax_number
            if tax_number and tax_number != "[Конфіденційна інформація]":
                cursor.execute(
                    "SELECT id FROM declarants WHERE tax_number = %s LIMIT 1", (tax_number,)
                )
                result = cursor.fetchone()
                if result:
                    declarant_id = result[0]

            # If not found by tax_number, try by unzr
            if not declarant_id and unzr and unzr != "[Конфіденційна інформація]":
                cursor.execute("SELECT id FROM declarants WHERE unzr = %s LIMIT 1", (unzr,))
                result = cursor.fetchone()
                if result:
                    declarant_id = result[0]

            cursor.execute(
                """INSERT INTO family_members (
                    declaration_id, declarant_id, lastname, firstname, middlename,
                    tax_number, unzr, passport,
                    subject_relation, citizenship,
                    country_id, region, district, community, city, city_type,
                    street, house_num, apartments_num, post_code,
                    raw_data, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                ) RETURNING id""",
                (
                    declaration_id,
                    declarant_id,  # Link to declarant if they exist
                    self._safe_str(member.get("lastname")),
                    self._safe_str(member.get("firstname")),
                    self._safe_str(member.get("middlename")),
                    tax_number,
                    unzr,
                    self._safe_str(member.get("passport")),
                    self._safe_str(member.get("subjectRelation")),
                    self._safe_int(member.get("citizenship")),
                    self._safe_int(member.get("country")),
                    self._safe_str(member.get("region")),
                    self._safe_str(member.get("district")),
                    self._safe_str(member.get("community")),
                    self._safe_str(member.get("city")),
                    self._safe_str(member.get("cityType")),
                    self._safe_str(member.get("street")),
                    self._safe_str(member.get("houseNum")),
                    self._safe_str(member.get("apartmentsNum")),
                    self._safe_str(member.get("postCode")),
                    json.dumps(member, ensure_ascii=False),
                ),
            )
            family_member_uuid = cursor.fetchone()[0]
            # Map internal ID to UUID for owner references
            internal_id = member.get("id")
            if internal_id:
                family_member_ids[internal_id] = family_member_uuid

        return family_member_ids

    # ========================================================================
    # REAL ESTATE
    # ========================================================================

    def _save_real_estate(
        self,
        declaration_id: str,
        step_3_data: list[dict],
        family_member_ids: dict[str, str],
        cursor,
    ):
        """Save real estate properties."""
        for prop in step_3_data:
            # Determine owner
            owner_type, family_member_id = self._determine_owner(
                prop.get("rights", []), family_member_ids
            )

            cursor.execute(
                """INSERT INTO real_estate (
                    declaration_id, owner_type, family_member_id,
                    object_type, total_area, ownership_type, ownership_date,
                    rights, country_id, region, district, community, city, city_type,
                    street, house_num, apartments_num, post_code,
                    cost_at_acquisition, cost_currency, cost_type,
                    reg_number, raw_data, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, NOW()
                )""",
                (
                    declaration_id,
                    owner_type,
                    family_member_id,
                    self._safe_str(prop.get("objectType")),
                    self._safe_decimal(prop.get("totalArea")),
                    self._get_first_ownership_type(prop.get("rights", [])),
                    self._safe_date(prop.get("owningDate")),
                    json.dumps(prop.get("rights", []), ensure_ascii=False),
                    self._safe_int(prop.get("country")),
                    self._safe_str(prop.get("region")),
                    self._safe_str(prop.get("district")),
                    self._safe_str(prop.get("community")),
                    self._safe_str(prop.get("city")),
                    self._safe_str(prop.get("cityType")),
                    self._safe_str(prop.get("ua_street") or prop.get("street")),
                    self._safe_str(prop.get("ua_houseNum") or prop.get("houseNum")),
                    self._safe_str(prop.get("ua_apartmentsNum") or prop.get("apartmentsNum")),
                    self._safe_str(prop.get("ua_postCode") or prop.get("postCode")),
                    self._safe_decimal(prop.get("cost_date_assessment")),
                    "UAH",
                    self._safe_str(prop.get("object_cost_type")),
                    self._safe_str(prop.get("regNumber")),
                    json.dumps(prop, ensure_ascii=False),
                ),
            )

    # ========================================================================
    # INCOME SOURCES
    # ========================================================================

    def _save_income_sources(
        self,
        declaration_id: str,
        step_11_data: list[dict],
        family_member_ids: dict[str, str],
        cursor,
    ):
        """Save income sources."""
        for income in step_11_data:
            owner_type, family_member_id = self._determine_owner(
                income.get("person", []), family_member_ids
            )

            cursor.execute(
                """INSERT INTO income_sources (
                    declaration_id, owner_type, family_member_id,
                    income_type, income_source, source_edrpou,
                    amount, currency,
                    raw_data, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )""",
                (
                    declaration_id,
                    owner_type,
                    family_member_id,
                    self._safe_str(income.get("objectType")),
                    self._safe_str(income.get("source")),
                    self._safe_str(income.get("edrpou")),
                    self._safe_decimal(income.get("sizeIncome")),
                    self._safe_str(income.get("currency", "UAH")),
                    json.dumps(income, ensure_ascii=False),
                ),
            )

    # ========================================================================
    # VEHICLES
    # ========================================================================

    def _save_vehicles(
        self,
        declaration_id: str,
        step_6_data: list[dict],
        family_member_ids: dict[str, str],
        cursor,
    ):
        """Save vehicles."""
        for vehicle in step_6_data:
            # Skip records without required objectType field
            object_type = self._safe_str(vehicle.get("objectType"))
            if not object_type:
                self.logger.warning(f"Skipping vehicle without objectType: {vehicle.keys()}")
                continue

            owner_type, family_member_id = self._determine_owner(
                vehicle.get("rights", []), family_member_ids
            )

            cursor.execute(
                """INSERT INTO vehicles (
                    declaration_id, owner_type, family_member_id,
                    object_type, brand, model, year,
                    reg_number, ownership_type, ownership_date, rights,
                    raw_data, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )""",
                (
                    declaration_id,
                    owner_type,
                    family_member_id,
                    object_type,
                    self._safe_str(vehicle.get("brand")),
                    self._safe_str(vehicle.get("model")),
                    self._safe_int(vehicle.get("graduationYear")),
                    self._safe_str(vehicle.get("object_identificationNumber")),
                    self._get_first_ownership_type(vehicle.get("rights", [])),
                    self._safe_date(vehicle.get("owningDate")),
                    json.dumps(vehicle.get("rights", []), ensure_ascii=False),
                    json.dumps(vehicle, ensure_ascii=False),
                ),
            )

    # ========================================================================
    # VALUABLES
    # ========================================================================

    def _save_valuables(
        self,
        declaration_id: str,
        step_4_data: list[dict],
        family_member_ids: dict[str, str],
        cursor,
    ):
        """Save valuables."""
        for valuable in step_4_data:
            # Skip records without required objectType field
            valuable_type = self._safe_str(valuable.get("objectType"))
            if not valuable_type:
                self.logger.warning(f"Skipping valuable without objectType: {valuable.keys()}")
                continue

            owner_type, family_member_id = self._determine_owner(
                valuable.get("rights", []), family_member_ids
            )

            cursor.execute(
                """INSERT INTO valuables (
                    declaration_id, owner_type, family_member_id,
                    valuable_type, description, total_value,
                    cost_currency, ownership_type, ownership_date, rights,
                    raw_data, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )""",
                (
                    declaration_id,
                    owner_type,
                    family_member_id,
                    valuable_type,
                    self._safe_str(valuable.get("description")),
                    self._safe_decimal(valuable.get("costDate")),
                    self._safe_str(valuable.get("costCurrency", "UAH")),
                    self._get_first_ownership_type(valuable.get("rights", [])),
                    self._safe_date(valuable.get("owningDate")),
                    json.dumps(valuable.get("rights", []), ensure_ascii=False),
                    json.dumps(valuable, ensure_ascii=False),
                ),
            )

    # ========================================================================
    # BANK ACCOUNTS
    # ========================================================================

    def _save_bank_accounts(
        self,
        declaration_id: str,
        step_17_data: list[dict],
        family_member_ids: dict[str, str],
        cursor,
    ):
        """Save bank accounts."""
        for account in step_17_data:
            owner_type, family_member_id = self._determine_owner(
                account.get("person_who_care", []), family_member_ids
            )

            cursor.execute(
                """INSERT INTO bank_accounts (
                    declaration_id, owner_type, family_member_id,
                    bank_name, bank_code, account_type,
                    ownership_type, rights, raw_data, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )""",
                (
                    declaration_id,
                    owner_type,
                    family_member_id,
                    self._safe_str(account.get("establishment_ua_company_name")),
                    self._safe_str(account.get("establishment_ua_company_code")),
                    self._safe_str(account.get("establishment_type")),
                    self._safe_str(account.get("ownership_type", "Власність")),
                    json.dumps(account.get("rights", []), ensure_ascii=False),
                    json.dumps(account, ensure_ascii=False),
                ),
            )

    # ========================================================================
    # LIABILITIES
    # ========================================================================

    def _save_liabilities(
        self,
        declaration_id: str,
        step_13_data: list[dict],
        family_member_ids: dict[str, str],
        cursor,
    ):
        """Save liabilities."""
        for liability in step_13_data:
            # Skip records without required objectType field
            liability_type = self._safe_str(liability.get("objectType"))
            if not liability_type:
                self.logger.warning(f"Skipping liability without objectType: {liability.keys()}")
                continue

            owner_type, family_member_id = self._determine_owner(
                liability.get("person_who_care", []), family_member_ids
            )

            cursor.execute(
                """INSERT INTO liabilities (
                    declaration_id, owner_type, family_member_id,
                    liability_type, creditor_name, creditor_edrpou,
                    outstanding_amount, currency, issue_date,
                    raw_data, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )""",
                (
                    declaration_id,
                    owner_type,
                    family_member_id,
                    liability_type,
                    self._safe_str(liability.get("emitent_ua_company_name")),
                    self._safe_str(liability.get("emitent_ua_company_code")),
                    self._safe_decimal(liability.get("credit_rest")),
                    self._safe_str(liability.get("currency", "UAH")),
                    self._safe_date(liability.get("dateOrigin")),
                    json.dumps(liability, ensure_ascii=False),
                ),
            )

    # ========================================================================
    # SECURITIES
    # ========================================================================

    def _save_securities(
        self,
        declaration_id: str,
        step_7_data: list[dict],
        family_member_ids: dict[str, str],
        cursor,
    ):
        """Save securities."""
        for security in step_7_data:
            # Try both 'objectType' and 'typeProperty' fields
            security_type = self._safe_str(
                security.get("objectType") or security.get("typeProperty")
            )
            if not security_type:
                self.logger.warning(
                    f"Skipping security without objectType/typeProperty: {security.keys()}"
                )
                continue

            owner_type, family_member_id = self._determine_owner(
                security.get("rights", []) or security.get("persons", []), family_member_ids
            )

            # Try multiple field names for issuer
            issuer_name = self._safe_str(
                security.get("emitent") or security.get("emitent_ua_company_name")
            )
            issuer_edrpou = self._safe_str(
                security.get("emitent_edrpou") or security.get("emitent_ua_company_code")
            )

            cursor.execute(
                """INSERT INTO securities (
                    declaration_id, owner_type, family_member_id,
                    security_type, issuer_name, issuer_edrpou,
                    quantity, total_value, cost_currency,
                    ownership_type, ownership_date, rights,
                    raw_data, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )""",
                (
                    declaration_id,
                    owner_type,
                    family_member_id,
                    security_type,
                    issuer_name,
                    issuer_edrpou,
                    self._safe_decimal(security.get("units") or security.get("amount")),
                    self._safe_decimal(security.get("cost")),
                    self._safe_str(security.get("currency", "UAH")),
                    self._get_first_ownership_type(
                        security.get("rights", []) or security.get("persons", [])
                    ),
                    self._safe_date(security.get("owningDate")),
                    json.dumps(
                        security.get("rights", []) or security.get("persons", []),
                        ensure_ascii=False,
                    ),
                    json.dumps(security, ensure_ascii=False),
                ),
            )

    # ========================================================================
    # CORPORATE RIGHTS
    # ========================================================================

    def _save_corporate_rights(
        self,
        declaration_id: str,
        step_8_data: list[dict],
        family_member_ids: dict[str, str],
        cursor,
    ):
        """Save corporate rights."""
        for corp_right in step_8_data:
            # Try both 'company_name' and 'name' fields
            company_name = self._safe_str(corp_right.get("company_name") or corp_right.get("name"))
            if not company_name:
                self.logger.warning(
                    f"Skipping corporate right without company_name/name: {corp_right.keys()}"
                )
                continue

            owner_type, family_member_id = self._determine_owner(
                corp_right.get("rights", []), family_member_ids
            )

            # Try multiple field names for company code
            company_code = self._safe_str(
                corp_right.get("company_code") or corp_right.get("corporate_rights_company_code")
            )

            cursor.execute(
                """INSERT INTO corporate_rights (
                    declaration_id, owner_type, family_member_id,
                    company_name, company_edrpou, ownership_percent,
                    ownership_type, ownership_date, rights,
                    raw_data, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )""",
                (
                    declaration_id,
                    owner_type,
                    family_member_id,
                    company_name,
                    company_code,
                    self._safe_decimal(
                        corp_right.get("share_percent") or corp_right.get("cost_percent")
                    ),
                    self._get_first_ownership_type(corp_right.get("rights", [])),
                    self._safe_date(corp_right.get("owningDate")),
                    json.dumps(corp_right.get("rights", []), ensure_ascii=False),
                    json.dumps(corp_right, ensure_ascii=False),
                ),
            )

    # ========================================================================
    # INTANGIBLE ASSETS
    # ========================================================================

    def _save_intangible_assets(
        self,
        declaration_id: str,
        step_9_data: list[dict],
        family_member_ids: dict[str, str],
        cursor,
    ):
        """Save intangible assets."""
        for asset in step_9_data:
            # Skip records without required objectType field
            asset_type = self._safe_str(asset.get("objectType"))
            if not asset_type:
                # Check if this is actually beneficial owner data (has different fields)
                if "address_beneficial_owner" in asset or "company_name_beneficial_owner" in asset:
                    # This is beneficial owner data, not intangible asset - skip silently
                    continue
                # Check if this is expense data (has expenseType)
                if "expenseType" in asset or "expenseSpec" in asset:
                    # This is expense data, not intangible asset - skip silently
                    continue
                self.logger.debug(f"Skipping intangible asset without objectType: {asset.keys()}")
                continue

            owner_type, family_member_id = self._determine_owner(
                asset.get("rights", []), family_member_ids
            )

            cursor.execute(
                """INSERT INTO intangible_assets (
                    declaration_id, owner_type, family_member_id,
                    asset_type, description, total_value,
                    cost_currency, ownership_type, ownership_date, rights,
                    raw_data, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )""",
                (
                    declaration_id,
                    owner_type,
                    family_member_id,
                    asset_type,
                    self._safe_str(asset.get("description")),
                    self._safe_decimal(asset.get("cost")),
                    self._safe_str(asset.get("currency", "UAH")),
                    self._get_first_ownership_type(asset.get("rights", [])),
                    self._safe_date(asset.get("owningDate")),
                    json.dumps(asset.get("rights", []), ensure_ascii=False),
                    json.dumps(asset, ensure_ascii=False),
                ),
            )

    # ========================================================================
    # EXPENSES
    # ========================================================================

    def _save_expenses(
        self,
        declaration_id: str,
        step_10_data: list[dict],
        family_member_ids: dict[str, str],
        cursor,
    ):
        """Save expenses (other property/assets)."""
        for expense in step_10_data:
            # Skip records without required fields (expense_type and amount are NOT NULL)
            expense_type = self._safe_str(expense.get("objectType"))
            # Field is called 'costDateOrigin' not 'cost'
            amount = self._safe_decimal(expense.get("costDateOrigin"))

            if not expense_type or amount is None:
                # Skip records with missing type or non-numeric/missing cost
                continue

            cursor.execute(
                """INSERT INTO expenses (
                    declaration_id, expense_type, description,
                    amount, currency, raw_data, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, NOW()
                )""",
                (
                    declaration_id,
                    expense_type,
                    # Field is called 'descriptionObject' not 'description'
                    self._safe_str(expense.get("descriptionObject")),
                    amount,
                    self._safe_str(expense.get("currency", "UAH")),
                    json.dumps(expense, ensure_ascii=False),
                ),
            )

    # ========================================================================
    # MEMBERSHIPS
    # ========================================================================

    def _save_memberships(
        self,
        declaration_id: str,
        step_5_data: list[dict],
        family_member_ids: dict[str, str],
        cursor,
    ):
        """Save memberships."""
        for membership in step_5_data:
            cursor.execute(
                """INSERT INTO memberships (
                    declaration_id, organization_name, organization_edrpou,
                    organization_type, role, raw_data, created_at
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, NOW()
                )""",
                (
                    declaration_id,
                    self._safe_str(membership.get("organization_name")),
                    self._safe_str(membership.get("organization_edrpou")),
                    self._safe_str(membership.get("organization_type")),
                    self._safe_str(membership.get("position")),
                    json.dumps(membership, ensure_ascii=False),
                ),
            )

    # ========================================================================
    # OWNER DETERMINATION
    # ========================================================================

    def _determine_owner(
        self, rights_or_person: list[dict], family_member_ids: dict[str, str]
    ) -> tuple[str, str | None]:
        """Determine owner type and family member ID from rights array.

        Returns:
            (owner_type, family_member_id)
        """
        if not rights_or_person:
            return ("declarant", None)

        for right in rights_or_person:
            # Handle case where API returns string instead of dict
            if isinstance(right, str):
                if right == "1":
                    return ("declarant", None)
                elif right in family_member_ids:
                    return ("family", family_member_ids[right])
                continue

            # Handle normal dict case
            if not isinstance(right, dict):
                continue

            right_belongs = right.get("rightBelongs") or right.get("person")
            if right_belongs == "1":
                return ("declarant", None)
            elif right_belongs in family_member_ids:
                return ("family", family_member_ids[right_belongs])

        return ("declarant", None)

    @staticmethod
    def _get_first_ownership_type(rights: list[dict]) -> str | None:
        """Get first ownership type from rights array."""
        if rights and len(rights) > 0:
            return rights[0].get("ownershipType")
        return None

    # ========================================================================
    # UTILITIES
    # ========================================================================

    def get_existing_ids(self, declaration_ids: list[str] | None = None) -> set:
        """Check which declaration IDs already exist in database.

        Args:
            declaration_ids: List of declaration IDs to check. If empty/None, returns ALL IDs.

        Returns:
            Set of IDs that already exist
        """
        with self._get_connection() as conn, conn.cursor() as cursor:
            if not declaration_ids:
                # Return ALL declaration IDs (for syncing with Redis)
                cursor.execute("SELECT document_id::text FROM declarations")
            else:
                # Return only specified IDs that exist
                cursor.execute(
                    "SELECT document_id::text FROM declarations WHERE document_id = ANY(%s::uuid[])",
                    (declaration_ids,),
                )
            return {row[0] for row in cursor.fetchall()}
