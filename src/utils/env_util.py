import os
from dotenv import load_dotenv
load_dotenv()

location = os.environ["AZURE_LOCATION"]
subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
resource_group = os.environ["AZURE_RESOURCE_GROUP"]
aifoundry_proj_name = os.environ["AZURE_AI_FOUNDRY_PROJECT_NAME"]

def get_aifound_proj_conn_string() -> str:
    """
    Get the connection string for the AI Foundry project.
    """

    connection_string =  f"{location}.api.azureml.ms;{subscription_id};{resource_group};{aifoundry_proj_name}"    
    
    return connection_string

def get_aisearch_conn() -> str:
    aisearch_conn_id = f"/subscriptions/{subscription_id}/resourceGroups/{resource_group}/providers/Microsoft.MachineLearningServices/workspaces/{aifoundry_proj_name}/connections/search-service-connection"
    return aisearch_conn_id
