param name string
param location string = resourceGroup().location
param tags object = {}

var cognitiveServicesOpenAIContributorRoleDefinitionId = resourceId('Microsoft.Authorization/roleDefinitions', 'a001fd3d-188f-4b5d-821b-7da978bf7442')

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' = {
  name: name
  location: location
  tags: union(tags, { 'azd-service-name': name })
}

resource cognitiveServicesOpenAIContributorRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(managedIdentity.id, cognitiveServicesOpenAIContributorRoleDefinitionId)
  scope: resourceGroup()
  properties: {
    roleDefinitionId: cognitiveServicesOpenAIContributorRoleDefinitionId
    principalId: managedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

output managedIdentityName string = managedIdentity.name
output managedIdentityClientId string = managedIdentity.properties.clientId
output managedIdentityPrincipalId string = managedIdentity.properties.principalId
