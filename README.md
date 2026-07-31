```text
  ▄▄▄▄▄▄                                             
 █▀██▀▀▀█▄                                   █▄      
   ██▄▄▄█▀▄                                 ▄██▄▄    
   ██▀▀▀  ████▄▄███▄ ▄██▀█ ████▄ ▄█▀█▄ ▄███▀ ██ ████▄
 ▄ ██     ██   ██ ██ ▀███▄ ██ ██ ██▄█▀ ██    ██ ██   
 ▀██▀    ▄█▀  ▄▀███▀█▄▄██▀▄████▀▄▀█▄▄▄▄▀███▄▄██▄█▀   
                           ██                        
                           ▀                          
```

## For Users (Where To Download)

1. Go to the [Releases page](../../releases) of this repo.
2. Download `Prospectr-Windows.zip` (Windows) or `Prospectr-Mac.zip` (Mac).
3. Unzip it and double-click `Prospectr`.
4. Your browser will open automatically to the app. Click the Settings button to paste in your Google Places and Supported AI API key. this only needs to be done once; the keys are saved next to the app.

## Getting And Using Keys

Inside the website you are required to obtain a Places(new) API Key from google cloud

The settings can be found here

<img src="assets/demonstrationA.gif" width="700" alt="Settings Demo">

### Places API(New)
1. Open Google Cloud Console

Go to: https://console.cloud.google.com/

Sign in with your Google account.

2. Create a Project
Click the Project dropdown at the top.
Click New Project.
Give it a name (for example, Prospectr).
Click Create.
Wait a few seconds and select the new project.


4. Enable Billing
Google requires billing to use the Places API.
Open the navigation menu.
Go to Billing.
Link a billing account to your project.
Google provides a monthly free credit for many Maps Platform APIs, so small projects often stay within the free usage limits.


5. Enable the Places API (New)
Open APIs & Services -> Library.
Search for:
Places API (New)
Click it.
Press Enable.


6. Create an API Key
Open APIs & Services -> Credentials.
Click + Create Credentials.
Select API Key.
Copy the generated API key.
Under API restrictions
Choose: Restrict key
Then select:
Places API(New)
Save the changes.


7. Paste the Key into Prospectr
Open Prospectr.
Click the Settings button.
Paste your Google Places API key into the Places API Key field.
Click Save.
Your key is stored locally and only needs to be entered once.

## For developers

Run from source (auto-reloads on code changes, good for development):

```bash

pip install -r requirements.txt

python core/app.py

```

## Building a new release

This repo uses GitHub Actions to build the Windows and Mac executable automatically. To publish a new version:

1. Commit your changes.
2. Tag the commit and push the tag, e.g.:

```bash

   git tag v1.0.0

   git push origin v1.0.0

```

GitHub Actions will build both executable (see the "Actions" tab for progress). Once done, download them from the workflow's build artifacts, zip each one, and attach them to a new GitHub Release so step 2 above for users has something to download.

