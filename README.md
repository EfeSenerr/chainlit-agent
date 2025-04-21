# Chainlit Agent: Intelligent Assistant with Azure AI Agent

[![Open in GitHub Codespaces](https://img.shields.io/static/v1?style=for-the-badge&label=GitHub+Codespaces&message=Open&color=brightgreen&logo=github)](https://github.com/codespaces/new?template_repository=zhenbzha/chainlit-agent&ref=main&location=WestEurope)
[![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/zhenbzha/chainlit-agent)


## Table of Contents

- [Overview](#overview)
- [Features](#features) 
- [Pre-Requisites](#pre-requisites)
- [Getting Started](#getting-started) 
    - [GitHub Codespaces](#github-codespaces) 
    - [VS Code Dev Containers](#vs-code-dev-containers) 
- [Development](#development) 
- [Testing](#testing) 
- [Guidance](#guidance)
    - [Costs](#costs)
    - [Security Guidelines](#security-guidelines)
        - [Required Security Measures](#required-security-measures)
        - [Authentication and Authorization](#authentication-and-authorization)
        - [Repository Security](#repository-security)
        - [Additional Security Considerations](#additional-security-considerations)
- [Resources](#resources) 
- [Code of Conduct](#code-of-conduct)
- [Responsible AI Guidelines](#responsible-ai-guidelines)

## Overview

This project implements an intelligent assistant that showcases:

1. Azure AI Foundry SDK for building, deploying, and managing AI applications at scale
2. Azure AI Agents for orchestrating complex tasks and building extensible AI solutions
3. A Chainlit-based chat interface for interactive user engagement
4. FastAPI endpoints for programmatic access

## Features

The project provides the following features:

- [Chainlit](https://docs.chainlit.io) for creating interactive chat interfaces
- [Azure OpenAI](https://learn.microsoft.com/azure/ai-services/openai/) for advanced language model capabilities
- [Azure AI Search](https://learn.microsoft.com/azure/search/search-what-is-azure-search) for semantic search and information retrieval
- [Azure AI Agents](https://learn.microsoft.com/azure/ai-services/agents/overview) for task orchestration
- [FastAPI](https://fastapi.tiangolo.com/) for REST API endpoints
- [Azure Container Apps](https://learn.microsoft.com/azure/container-apps/overview) for cloud-native application hosting
- Docker containerization for deployment flexibility

It also comes with:
- Sample implementation of both chat and API interfaces
- Development environment setup with VS Code
- Azure service integration examples
- Deployment configurations for Azure
- Pre-populated with Contoso sample data (customizable for your specific data needs)

## Pre-requisites

To deploy and explore the sample, you will need:

1. An active Azure subscription - [Signup for a free account here](https://azure.microsoft.com/free/)
1. Azure OpenAI Services - [Learn about Azure OpenAI](https://learn.microsoft.com/azure/ai-services/openai/)
1. Azure AI Search service - [Learn more about AI Search](https://learn.microsoft.com/azure/search/search-what-is-azure-search)
1. Available Quota for GPT models in your preferred region

From a tooling perspective, familiarity with the following is useful:
 - Visual Studio Code (and extensions)
 - Python and FastAPI
 - Docker and containerization
 - Azure services and deployment

## Getting Started

You have two options for setting up your development environment:

1. Use GitHub Codespaces - for a prebuilt dev environment in the cloud
2. Use Docker Desktop - for a prebuilt dev environment on local device

Choose the option that best suits your needs and development style.

### GitHub Codespaces

1. You can run this template virtually by using GitHub Codespaces. Click this button to open a web-based VS Code instance in your browser:

    [![Open in GitHub Codespaces](https://img.shields.io/static/v1?style=for-the-badge&label=GitHub+Codespaces&message=Open&color=brightgreen&logo=github)](https://github.com/codespaces/new?template_repository=zhenbzha/chainlit-agent&ref=main&location=WestEurope
    )

1. Once the codespaces environment is ready (this can take several minutes), open a new terminal in that VS Code instance - and proceed to the [Development](#development) step.

### VS Code Dev Containers

A related option is to use VS Code Dev Containers, which will open the project in your _local Visual Studio Code editor_ using the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers):

1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop) (if not installed), then start it.
1. Open the project in your local VS Code by clicking the button below:
   
    [![Open in Dev Containers](https://img.shields.io/static/v1?style=for-the-badge&label=Dev%20Containers&message=Open&color=blue&logo=visualstudiocode)](https://vscode.dev/redirect?url=vscode://ms-vscode-remote.remote-containers/cloneInVolume?url=https://github.com/yourusername/chainlit-agent)

1. Once the VS Code window shows the project files (this can take several minutes), open a new terminal in that VS Code instance - and proceed to the [Development](#development) step.

## Development

Once you've completed the setup the project (using [Codespaces](#github-codespaces), [Dev Containers](#vs-code-dev-containers)), you should now have a Visual Studio Code editor open, with the project files loaded, and a terminal open for running commands. Let's verify that all required tools are installed.

```bash
az version
azd version
python --version
```

We can now proceed with next steps - click to expand for detailed instructions.

<details>
<summary> 1️⃣ | Authenticate With Azure </summary>

1. Open a VS Code terminal and authenticate with Azure CLI. Use the `--use-device-code` option if authenticating from GitHub Codespaces. Complete the auth workflow as guided.

    ```bash
    az login --use-device-code
    ```
1. Now authenticate with Azure Developer CLI in the same terminal. Complete the auth workflow as guided. 

    ```bash
    azd auth login --use-device-code
    ```
1. You should see: **Logged in on Azure.** This will create a folder under `.azure/` in your project to store the configuration for this deployment. You may have multiple azd environments if desired.

</details>

<details>
<summary> 2️⃣ |  Provision-Deploy with AZD </summary>

1. Run `azd up` to provision infrastructure _and_ deploy the application, with one command. (You can also use `azd provision`, `azd deploy` separately if needed)

    ```bash
    azd up
    ```
1. You will be asked for  a _subscription_ for provisioning resources, an _environment name_ that maps to the resource group, and a _location_ for deployment. Refer to the [Region Availability](#region-availability) guidance to select the region that has the desired models and quota available.
1. The `azd up` command can take 15-20 minutes to complete. Successful completion sees a **`SUCCESS: ...`** messages posted to the console. We can now validate the outcomes.
</details>

<details>
<summary> 3️⃣ | Validate and Deploy </summary>

1. Test the FastAPI backend:
   - Get the API URL from the `azd up` output
   - Visit `https://<your-api-app>.azurecontainerapps.io/docs` in your browser
   - You should see the Swagger UI documentation
   - Test the `/api/test` endpoint with a sample query
   - Verify that responses from Azure OpenAI are working

2. Test the Chainlit interface:
   - Get the Chainlit URL from the `azd up` output
   - Visit `https://<your-chainlit-app>.azurecontainerapps.io` in your browser
   - You should see the Chainlit chat interface
   - Try a test conversation
   - Verify that the chat responses are working correctly

✅ | **Congratulations!** - Your development environment is ready!

</details>

## Testing

To test the application in your local environment:

1. Start the FastAPI backend:
    ```bash
    ./start_fastapi.sh
    ```   This will start the API server on http://localhost:8000

2. Start the Chainlit interface:
    ```bash
    ./start_chainlit.sh
    ```

3. Testing the Components:
   - For API: Access http://localhost:8000/docs to test endpoints via Swagger UI
   - For Chat: Access http://localhost to test the chat interface
   - Try different types of queries to ensure proper handling
   - Verify Azure service integrations are working correctly

## Guidance

### Costs

Pricing varies per region and usage, so it isn't possible to predict exact costs for your usage. The majority of the Azure resources used in this infrastructure are on usage-based pricing tiers. However, Azure Container Registry has a fixed cost per registry per day.

You can try the Azure pricing calculator for the resources:

* Azure OpenAI Service: S0 tier, GPT-4 model. Pricing is based on token count.
* Azure Container App: Consumption tier with 0.5 CPU, 1GiB memory/storage. Pricing is based on resource allocation, and each month allows for a certain amount of free usage.
* Azure Container Registry: Basic tier.
* Log analytics: Pay-as-you-go tier. Costs based on data ingested.

⚠️ To avoid unnecessary costs, remember to take down your app if it's no longer in use, either by deleting the resource group in the Portal or running `azd down`.

### Security Guidelines

This repository contains sample code and guidance for demonstration and learning purposes. It is not intended for production use without proper review and adaptation. 

#### Required Security Measures

Before deploying to production:
- Ensure proper security measures are implemented
- Add appropriate error handling and logging
- Test thoroughly in your environment
- Follow your organization's deployment and security guidelines

#### Authentication and Authorization

This template uses [Managed Identity](https://learn.microsoft.com/entra/identity/managed-identities-azure-resources/overview) for all Azure service communication.

#### Repository Security

To ensure continued best practices in your own repository, we recommend that anyone creating solutions based on our templates ensure that the [Github secret scanning](https://docs.github.com/code-security/secret-scanning/about-secret-scanning) setting is enabled.

#### Additional Security Considerations

Consider implementing these additional security measures:

* Enable Microsoft Defender for Cloud to [secure your Azure resources](https://learn.microsoft.com/en-us/azure/defender-for-cloud/defender-for-cloud-introduction)
* Protect the Azure Container Apps instance with:
  * [Web Application Firewall](https://learn.microsoft.com/azure/container-apps/waf-app-gateway)
  * [Virtual Network Integration](https://learn.microsoft.com/azure/container-apps/networking?tabs=workload-profiles-env%2Cazure-cli)

## Resources

1. [Chainlit Documentation](https://docs.chainlit.io)
2. [Azure OpenAI Documentation](https://learn.microsoft.com/azure/ai-services/openai/)
3. [Azure AI Search Documentation](https://learn.microsoft.com/azure/search/search-what-is-azure-search)
4. [Azure AI Agents Documentation](https://learn.microsoft.com/azure/ai-services/agents/overview)
5. [FastAPI Documentation](https://fastapi.tiangolo.com)

## Code of Conduct

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/). Learn more here:

- [Microsoft Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/)
- Contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with questions or concerns

## Responsible AI Guidelines

This project follows Microsoft's responsible AI guidelines and best practices:

- [Microsoft Responsible AI Guidelines](https://www.microsoft.com/en-us/ai/responsible-ai)
- [Responsible AI practices for Azure OpenAI models](https://learn.microsoft.com/en-us/legal/cognitive-services/openai/overview)

---
