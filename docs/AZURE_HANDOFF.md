# Azure handoff for hackathon day

Nothing in this handoff creates Azure resources or makes paid API calls by itself. The API can be built and tested locally now; cloud commands are for when the team has access and knows the permitted subscription, region, registry, and host.

## Local container check

From the repository root, with Docker running:

```bash
docker build -t htc-api:local .
docker run --rm -p 8000:8000 htc-api:local
```

In another terminal:

```bash
python scripts/smoke_api.py http://127.0.0.1:8000
```

The image includes only the API code, two January CSVs, and the saved 1-hour model needed by those routes. It serves a retrospective demonstration; it does not call Azure Maps, Aurora, or any other weather service. If the team receives a VM or another container host instead of Container Apps, the same image listens on port 8000.

## If the team receives Azure Container Apps access

Use a **known existing** resource group, Container Apps environment with a Consumption workload profile, and image registry when possible. The deploy helper does not create a registry, environment, Log Analytics workspace, or resource group. It does not build or publish an image. Confirm the team's approved region and subscription before doing any of that work.

First publish the image to an approved registry. For a Linux AMD64 host, the build command is:

```bash
export HTC_IMAGE='YOUR_REGISTRY/htc-api:YOUR_COMMIT_SHA'
docker buildx build --platform linux/amd64 --tag "$HTC_IMAGE" --push .
```

The registry must be pullable by Container Apps. Use the team's existing registry credentials or managed identity; the helper assumes image pull access is already configured. An immutable commit tag or digest makes the demo reproducible.

Set the target values, inspect the command, then deliberately execute it:

```bash
export HTC_SUBSCRIPTION_ID='YOUR_SUBSCRIPTION_ID'
export HTC_RESOURCE_GROUP='EXISTING_RESOURCE_GROUP'
export HTC_ENVIRONMENT='EXISTING_CONTAINER_APPS_ENVIRONMENT'
export HTC_APP_NAME='htc-api'
scripts/azure_container_app.sh
scripts/azure_container_app.sh --execute
```

The preview makes **no Azure request**. `--execute` requires the active Azure CLI subscription to match `HTC_SUBSCRIPTION_ID`, then creates one app with external HTTP ingress on port 8000, **0–1 replicas**, **0.5 vCPU / 1 GiB**, a Consumption profile, and one active revision. Save the returned hostname and run `python scripts/smoke_api.py https://YOUR_HOSTNAME`. That smoke check makes one health request and one demo request. If the team has no Container Apps environment, decide whether to create one only after checking the subscription budget and the organiser's hosting instructions.

## Cost controls and limits

- Container Apps Consumption can scale to zero and has monthly free grants, but active compute and requests can be billed after those grants. A cold start is expected after idle time. [Microsoft billing](https://learn.microsoft.com/en-us/azure/container-apps/billing), [scaling](https://learn.microsoft.com/en-us/azure/container-apps/scale-app).
- A private registry, logging workspace, networking, and other Azure resources can have separate charges. Reusing team resources avoids creating them for this demo. Azure CLI's environment command defaults to a Log Analytics destination unless configured otherwise. [Microsoft environment CLI](https://learn.microsoft.com/en-us/cli/azure/containerapp/env?view=azure-cli-latest).
- No scheduled weather requests, GPU jobs, Foundry jobs, or training run are configured. Add a forecast provider only when its access, sample payload, usage limits, and issue-time semantics are confirmed.
- After the event, remove the app if it is no longer needed. Keep the resource group and shared environment if teammates use them. Check the actual subscription's cost dashboard and set a budget alert before publishing a public demo.

The current model uses measured grid state at time `t` for a target one hour later. The deployment does not turn it into a day-ahead forecast or prove avoided dispatch-down.
