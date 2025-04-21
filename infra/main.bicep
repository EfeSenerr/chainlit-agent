targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name which is used to generate a short unique hash for each resource')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
@metadata({
  azd: {
    type: 'location'
  }
})
param location string

@description('The name of the resource group for the OpenAI resource')
param openAiResourceGroupName string = ''

param containerRegistryName string = ''
param aiHubName string = ''
@description('The Azure AI Studio project name. If ommited will be generated')
param aiProjectName string = ''
@description('The application insights resource name. If ommited will be generated')
param applicationInsightsName string = ''
@description('The Open AI resource name. If ommited will be generated')
param openAiName string = ''
param keyVaultName string = ''
@description('The Azure Storage Account resource name. If ommited will be generated')
param storageAccountName string = ''

@description('The Azure Search connection name. If ommited will use a default value')
param searchConnectionName string = ''
var abbrs = loadJsonContent('./abbreviations.json')
@description('The log analytics workspace name. If ommited will be generated')
param logAnalyticsWorkspaceName string = ''
param useApplicationInsights bool = true
param useContainerRegistry bool = true
param useSearch bool = true
var aiConfig = loadYamlContent('./ai.yaml')

@description('The API version of the OpenAI resource')
param openAiApiVersion string = ' 2025-03-01-preview'

@description('The type of the OpenAI resource')
param openAiType string = 'azure'

@description('The name of the search service')
param searchServiceName string = ''

@description('The name of the OpenAI embedding deployment')
param openAiEmbeddingDeploymentName string = 'text-embedding-3-large'

@description('The name of the AI search index')
param aiSearchIndexName string

// this needs to align with the model defined in ai.yaml
@description('The name of the OpenAI deployment')
param openAiDeploymentName string = 'gpt-4o'

@description('Id of the user or app to assign application roles')
param principalId string = ''

@description('Whether the deployment is running on GitHub Actions')
param runningOnGh string = ''

var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))
var tags = { 'azd-env-name': environmentName }

resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-11-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}

resource openAiResourceGroup 'Microsoft.Resources/resourceGroups@2024-11-01' existing = {
  name: !empty(openAiResourceGroupName) ? openAiResourceGroupName : resourceGroup.name
}

var prefix = toLower('${environmentName}-${resourceToken}')

// USER ROLES
var principalType = empty(runningOnGh) ? 'User' : 'ServicePrincipal'
module managedIdentity 'core/security/managed-identity.bicep' = {
  name: 'managed-identity'
  scope: resourceGroup
  params: {
    name: 'id-${resourceToken}'
    location: location
    tags: tags
  }
}

module ai 'core/host/ai-environment.bicep' = {
  name: 'ai'
  scope: resourceGroup
  params: {
    location: location
    tags: tags
    hubName: !empty(aiHubName) ? aiHubName : 'ai-hub-${resourceToken}'
    projectName: !empty(aiProjectName) ? aiProjectName : 'ai-project-${resourceToken}'
    keyVaultName: !empty(keyVaultName) ? keyVaultName : '${abbrs.keyVaultVaults}${resourceToken}'
    storageAccountName: !empty(storageAccountName)
      ? storageAccountName
      : '${abbrs.storageStorageAccounts}${resourceToken}'
    openAiName: !empty(openAiName) ? openAiName : 'aoai-${resourceToken}'
    openAiModelDeployments: array(aiConfig.?deployments ?? [])
    logAnalyticsName: !useApplicationInsights
      ? ''
      : !empty(logAnalyticsWorkspaceName)
          ? logAnalyticsWorkspaceName
          : '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
    applicationInsightsName: !useApplicationInsights
      ? ''
      : !empty(applicationInsightsName) ? applicationInsightsName : '${abbrs.insightsComponents}${resourceToken}'
    containerRegistryName: !useContainerRegistry
      ? ''
      : !empty(containerRegistryName) ? containerRegistryName : '${abbrs.containerRegistryRegistries}${resourceToken}'
    searchServiceName: !useSearch ? '' : !empty(searchServiceName) ? searchServiceName : '${abbrs.searchSearchServices}${resourceToken}'
    searchConnectionName: !useSearch ? '' : !empty(searchConnectionName) ? searchConnectionName : 'search-service-connection'
  }
}

// Container apps host (including container registry)
module containerApps 'core/host/container-apps.bicep' = {
  name: 'container-apps'
  scope: resourceGroup
  params: {
    name: 'app'
    location: location
    tags: tags
    containerAppsEnvironmentName: '${prefix}-containerapps-env'
    containerRegistryName: ai.outputs.containerRegistryName
    logAnalyticsWorkspaceName: ai.outputs.logAnalyticsWorkspaceName
  }
}

module api 'app/api.bicep' = {
  name: 'api'
  scope: resourceGroup
  params: {
    name: replace('${take(prefix, 19)}-api', '--', '-')
    location: location
    tags: tags
    identityName: managedIdentity.outputs.managedIdentityName
    identityId: managedIdentity.outputs.managedIdentityClientId
    containerAppsEnvironmentName: containerApps.outputs.environmentName
    containerRegistryName: containerApps.outputs.registryName
    openAiDeploymentName: openAiDeploymentName
    openAiEmbeddingDeploymentName: openAiEmbeddingDeploymentName
    openAiEndpoint: ai.outputs.openAiEndpoint
    openAiType: openAiType
    openAiApiVersion: openAiApiVersion
    aiSearchEndpoint: ai.outputs.searchServiceEndpoint
    aiSearchIndexName: aiSearchIndexName
    appinsights_Connectionstring: ai.outputs.applicationInsightsConnectionString
    aifoundryProjName: ai.outputs.projectName
  }
}

module web 'app/web.bicep' = {
  name: 'web'
  scope: resourceGroup
  params: {
    name: replace('${take(prefix, 19)}-web', '--', '-')
    location: location
    tags: tags
    identityName: managedIdentity.outputs.managedIdentityName
    identityId: managedIdentity.outputs.managedIdentityClientId
    containerAppsEnvironmentName: containerApps.outputs.environmentName
    containerRegistryName: containerApps.outputs.registryName
    appinsights_Connectionstring: ai.outputs.applicationInsightsConnectionString
    aifoundryProjName: ai.outputs.projectName
    apiUrl: api.outputs.SERVICE_API_URI
  }
}

module aiSearchRole 'core/security/role.bicep' = {
  scope: resourceGroup
  name: 'ai-search-index-data-contributor'
  params: {
    principalId: managedIdentity.outputs.managedIdentityPrincipalId
    roleDefinitionId: '8ebe5a00-799e-43f5-93ac-243d3dce84a7' // Search Index Data Contributor
    principalType: 'ServicePrincipal'
  }
}

module appinsightsAccountRole 'core/security/role.bicep' = {
  scope: resourceGroup
  name: 'appinsights-account-role'
  params: {
    principalId: managedIdentity.outputs.managedIdentityPrincipalId
    roleDefinitionId: '3913510d-42f4-4e42-8a64-420c390055eb' // Monitoring Metrics Publisher
    principalType: 'ServicePrincipal'
  }
}

module userAiSearchRole 'core/security/role.bicep' = if (!empty(principalId)) {
  scope: resourceGroup
  name: 'user-ai-search-index-data-contributor'
  params: {
    principalId: principalId
    roleDefinitionId: '8ebe5a00-799e-43f5-93ac-243d3dce84a7' // Search Index Data Contributor
    principalType: principalType
  }
}

module openaiRoleUser 'core/security/role.bicep' = if (!empty(principalId)) {
  scope: resourceGroup
  name: 'user-openai-user'
  params: {
    principalId: principalId
    roleDefinitionId: 'a001fd3d-188f-4b5d-821b-7da978bf7442' // Cognitive Services OpenAI Contributor
    principalType: principalType
  }
}

module aiDeveloperRoleUser 'core/security/role.bicep' = {
  scope: resourceGroup
  name: 'user-azure-ai-developer'
  params: {
    principalId: managedIdentity.outputs.managedIdentityPrincipalId
    roleDefinitionId: '64702f94-c441-49e6-a78b-ef80e0188fee' // Azure AI Developer
    principalType: 'ServicePrincipal'
  }
}

output AZURE_SUBSCRIPTION_ID string = subscription().subscriptionId
output AZURE_LOCATION string = location
output AZURE_RESOURCE_GROUP string = resourceGroup.name

output MANAGED_IDENTITY_CLIENT_ID string = managedIdentity.outputs.managedIdentityClientId

output AZURE_OPENAI_CHAT_DEPLOYMENT string = openAiDeploymentName
output AZURE_OPENAI_API_VERSION string = openAiApiVersion
output AZURE_OPENAI_ENDPOINT string = ai.outputs.openAiEndpoint
output AZURE_OPENAI_NAME string = ai.outputs.openAiName
output AZURE_AI_FOUNDRY_PROJECT_NAME string = ai.outputs.projectName
output AZURE_OPENAI_RESOURCE_GROUP string = openAiResourceGroup.name
output AZURE_OPENAI_RESOURCE_GROUP_LOCATION string = openAiResourceGroup.location

output SERVICE_API_NAME string = api.outputs.SERVICE_API_NAME
output SERVICE_API_URI string = api.outputs.SERVICE_API_URI
output SERVICE_API_IMAGE_NAME string = api.outputs.SERVICE_API_IMAGE_NAME

output SERVICE_WEB_NAME string = web.outputs.SERVICE_WEB_NAME
output SERVICE_WEB_URI string = web.outputs.SERVICE_WEB_URI
output SERVICE_WEB_IMAGE_NAME string = web.outputs.SERVICE_WEB_IMAGE_NAME

output AZURE_CONTAINER_ENVIRONMENT_NAME string = containerApps.outputs.environmentName
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerApps.outputs.registryLoginServer
output AZURE_CONTAINER_REGISTRY_NAME string = containerApps.outputs.registryName

output APPINSIGHTS_CONNECTIONSTRING string = ai.outputs.applicationInsightsConnectionString

output OPENAI_TYPE string = 'azure'
output AZURE_EMBEDDING_NAME string = openAiEmbeddingDeploymentName

output AZURE_SEARCH_ENDPOINT string = ai.outputs.searchServiceEndpoint
output AZURE_SEARCH_NAME string = ai.outputs.searchServiceName

output AZURE_SEARCH_INDEX string = aiSearchIndexName
