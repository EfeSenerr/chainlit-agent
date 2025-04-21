using './main.bicep'

param environmentName = readEnvironmentVariable('AZURE_ENV_NAME', 'MY_ENV')
param location = readEnvironmentVariable('AZURE_LOCATION', 'canadaeast')
// in local env, it will be user's principal, who does the deployment
// in github action, it will be the service principal for github action. you create that with azd pipeline
param principalId = readEnvironmentVariable('AZURE_PRINCIPAL_ID', '')

param aiSearchIndexName  = readEnvironmentVariable('AZURE_SEARCH_INDEX', 'contoso-products')
// this will be set by github action
param runningOnGh = readEnvironmentVariable('GITHUB_ACTIONS', '')

