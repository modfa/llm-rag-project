import os
import json
import requests
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Debug: Print environment variables
print("Environment variables loaded:")
print(f"GRAFANA_USER: {os.getenv('GRAFANA_ADMIN_USER')}")
print(f"GRAFANA_PASSWORD: {'*' * len(os.getenv('GRAFANA_ADMIN_PASSWORD')) if os.getenv('GRAFANA_ADMIN_PASSWORD') else 'Not set'}")
print(f"GRAFANA_URL: {os.getenv('GRAFANA_URL', 'http://localhost:3000')}")

GRAFANA_URL = "http://localhost:3000"
GRAFANA_USER = os.getenv("GRAFANA_ADMIN_USER")
GRAFANA_PASSWORD = os.getenv("GRAFANA_ADMIN_PASSWORD")

PG_HOST = os.getenv("POSTGRES_HOST")
PG_DB = os.getenv("POSTGRES_DB")
PG_USER = os.getenv("POSTGRES_USER")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD")
PG_PORT = os.getenv("POSTGRES_PORT")

def create_service_account():
    auth = (GRAFANA_USER, GRAFANA_PASSWORD)
    print("\nAttempting to create service account:")
    print(f"URL: {GRAFANA_URL}/api/serviceaccounts")
    print(f"Using username: {GRAFANA_USER}")
    print(f"Password is {'set' if GRAFANA_PASSWORD else 'not set'}")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    # Service account payload
    sa_payload = {
        "name": "GrafanaServiceAccount",
        "role": "Admin",
        "isDisabled": False
    }
    
    try:
        # First, test basic authentication
        test_response = requests.get(
            f"{GRAFANA_URL}/api/org",
            auth=auth,
            verify=False
        )
        print(f"\nTest authentication response:")
        print(f"Status code: {test_response.status_code}")
        print(f"Response: {test_response.text}")

        if test_response.status_code != 200:
            print("Basic authentication failed!")
            return None

        # Check if service account already exists
        list_response = requests.get(
            f"{GRAFANA_URL}/api/serviceaccounts",
            auth=auth,
            verify=False
        )
        
        existing_sa = None
        if list_response.status_code == 200:
            for sa in list_response.json():
                if sa["name"] == "GrafanaServiceAccount":
                    existing_sa = sa
                    break

        if existing_sa:
            print(f"\nService account already exists with id: {existing_sa['id']}")
            sa_id = existing_sa['id']
        else:
            # Create new service account
            response = requests.post(
                f"{GRAFANA_URL}/api/serviceaccounts",
                auth=auth,
                headers=headers,
                json=sa_payload,
                verify=False
            )
            
            print(f"\nService account creation response:")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code != 201:
                print("Failed to create service account")
                return None
                
            sa_id = response.json().get("id")

        # Create token for the service account
        token_payload = {
            "name": "ServiceAccountToken",
            "role": "Admin"
        }
        
        token_response = requests.post(
            f"{GRAFANA_URL}/api/serviceaccounts/{sa_id}/tokens",
            auth=auth,
            headers=headers,
            json=token_payload,
            verify=False
        )
        
        print(f"\nToken creation response:")
        print(f"Status code: {token_response.status_code}")
        
        if token_response.status_code in [200, 201]:
            return token_response.json().get("key")
        else:
            print(f"Failed to create token: {token_response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {str(e)}")
        return None

def create_or_update_datasource(api_key):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    datasource_payload = {
        "name": "PostgreSQL",
        "type": "postgres",
        "url": f"{PG_HOST}:{PG_PORT}",
        "access": "proxy",
        "user": PG_USER,
        "database": PG_DB,
        "basicAuth": False,
        "isDefault": True,
        "jsonData": {"sslmode": "disable", "postgresVersion": 1300},
        "secureJsonData": {"password": PG_PASSWORD},
    }

    print("\nDatasource payload:")
    print(json.dumps(datasource_payload, indent=2))

    # First, try to get the existing datasource
    response = requests.get(
        f"{GRAFANA_URL}/api/datasources/name/{datasource_payload['name']}",
        headers=headers,
        verify=False
    )

    if response.status_code == 200:
        # Datasource exists, let's update it
        existing_datasource = response.json()
        datasource_id = existing_datasource["id"]
        print(f"Updating existing datasource with id: {datasource_id}")
        response = requests.put(
            f"{GRAFANA_URL}/api/datasources/{datasource_id}",
            headers=headers,
            json=datasource_payload,
            verify=False
        )
    else:
        # Datasource doesn't exist, create a new one
        print("Creating new datasource")
        response = requests.post(
            f"{GRAFANA_URL}/api/datasources",
            headers=headers,
            json=datasource_payload,
            verify=False
        )

    print(f"Response status code: {response.status_code}")
    print(f"Response headers: {response.headers}")
    print(f"Response content: {response.text}")

    if response.status_code in [200, 201]:
        print("Datasource created or updated successfully")
        return response.json().get("datasource", {}).get("uid") or response.json().get("uid")
    else:
        print(f"Failed to create or update datasource: {response.text}")
        return None

def create_dashboard(api_key, datasource_uid):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    dashboard_file = "dashboard.json"

    try:
        with open(dashboard_file, "r") as f:
            dashboard_json = json.load(f)
    except FileNotFoundError:
        print(f"Error: {dashboard_file} not found.")
        return
    except json.JSONDecodeError as e:
        print(f"Error decoding {dashboard_file}: {str(e)}")
        return

    print("Dashboard JSON loaded successfully.")

    # Update datasource UID in the dashboard JSON
    panels_updated = 0
    for panel in dashboard_json.get("panels", []):
        if isinstance(panel.get("datasource"), dict):
            panel["datasource"]["uid"] = datasource_uid
            panels_updated += 1
        elif isinstance(panel.get("targets"), list):
            for target in panel["targets"]:
                if isinstance(target.get("datasource"), dict):
                    target["datasource"]["uid"] = datasource_uid
                    panels_updated += 1

    print(f"Updated datasource UID for {panels_updated} panels/targets.")

    # Remove keys that shouldn't be included when creating a new dashboard
    dashboard_json.pop("id", None)
    dashboard_json.pop("uid", None)
    dashboard_json.pop("version", None)

    # Prepare the payload
    dashboard_payload = {
        "dashboard": dashboard_json,
        "overwrite": True,
        "message": "Updated by Python script",
    }

    print("Sending dashboard creation request...")

    response = requests.post(
        f"{GRAFANA_URL}/api/dashboards/db",
        headers=headers,
        json=dashboard_payload,
        verify=False
    )

    print(f"Response status code: {response.status_code}")
    print(f"Response content: {response.text}")

    if response.status_code == 200:
        print("Dashboard created successfully")
        return response.json().get("uid")
    else:
        print(f"Failed to create dashboard: {response.text}")
        return None

def main():
    api_key = create_service_account()
    if not api_key:
        print("Service account creation failed")
        return

    datasource_uid = create_or_update_datasource(api_key)
    if not datasource_uid:
        print("Datasource creation failed")
        return

    create_dashboard(api_key, datasource_uid)

if __name__ == "__main__":
    main()