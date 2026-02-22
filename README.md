# Gym Booking Automation

An automated Azure Function (v2) written in Python that books gym classes precisely when the booking window opens.

## Features

- **Automated Scheduling**: Runs daily via a Timer Trigger at 08:00:05 AM (Europe/Luxembourg).
- **Multi-User Support**: Processes bookings sequentially for multiple users based on their usernames (emails).
- **Managed Identity**: Uses Azure Managed Identity (`DefaultAzureCredential`) for secure access to Azure App Configuration.
- **Flexible Configuration**: Supports both local `config.yaml` and Azure App Configuration.
- **Robust Logic**: 
  - Matches classes based on the `bookingOpensOn` date provided by the API.
  - Precise timing with a 5-second buffer to ensure the booking window is open.
  - Comprehensive logging including API error payloads for troubleshooting.

## Project Structure

```text
gym-booking-automation/
├── function_app.py          # Azure Function entry point & orchestration
├── src/
│   ├── config.py            # Configuration loader (AppConfig vs Local YAML)
│   ├── models.py            # Pydantic data models for type safety
│   └── service.py           # Gym API client
├── config.yaml              # Local configuration (Git ignored)
├── local.settings.json      # Local Function settings
├── requirements.txt         # Python dependencies
└── .github/workflows/       # Automated deployment & config sync
```

## Setup & Configuration

### 1. Local Configuration
Create a `config.yaml` in the root directory (excluded from git):

```yaml
app_id: "EC1D38D7-D359-48D0-A60C-D8C0B8FB9DF9"
client: "enduserweb"
client_version: "1.13.10-1629,enduserweb"
facility_id: "334e683b-fd35-4076-95be-c32c233d1e46"
users:
  - username: "user@example.com"
    password: "${USER_PASSWORD}"
classes:
  - name: "AQUA POWER"
    weekday: "Tuesday"
    opening_hour: "08:00:00+01:00"
    user_names: ["user@example.com"]
```

### 2. Secrets Management
The script substitutes placeholders like `${VAR_NAME}` with environment variables.
- **Local**: Add variables to `local.settings.json` under `Values`.
- **Azure**: Add as Environment Variables in the Function App.

### 3. Azure Infrastructure
- **App Configuration**: Create an Azure App Configuration instance.
- **Managed Identity**: Enable System-Assigned Identity on the Function App.
- **Role Assignment**: Assign the **"App Configuration Data Reader"** role to the Function App's identity on the App Configuration resource.
- **Application Setting**: Set `AZURE_APP_CONFIG_ENDPOINT` to your AppConfig URL.

## Deployment

Deployment is automated via GitHub Actions (`.github/workflows/deploy.yml`). It performs the following:
1. Provisions/Updates common keys in Azure App Configuration.
2. Serializes the `users` and `classes` lists into AppConfig keys.
3. Deploys the Python code to the Azure Function App.

## Troubleshooting

- **Logs**: Monitor execution via Azure Portal -> Function App -> Log Stream or Application Insights.
- **Time Zone**: Ensure `WEBSITE_TIME_ZONE` is set to `Europe/Luxembourg` in Azure settings.
- **API Errors**: The script logs the full JSON payload from the API on failure for easier debugging.

## Disclaimer

This script is for personal use and automation purposes. Ensure your usage complies with the gym's terms of service.
