# YSU Campus Network Auto Login

Auto login script for Yanshan University campus network on Windows.

This project is designed for one practical goal: when the campus network drops or requires authentication again, the script checks the network and logs in automatically, while trying to avoid conflicts with Clash Verge.

## What It Does

- Checks whether the network is really online
- Avoids treating the campus login page as normal internet access
- Tries direct portal login first
- Falls back to the old CAS flow if needed
- Works with single-run mode, daemon mode, and Windows scheduled tasks
- Uses `curl --noproxy '*'` to reduce proxy and TUN interference

## Requirements

- Windows 10 or Windows 11
- Python 3.9 or later
- `curl.exe` available in the system
- Connected to YSU campus Wi-Fi or wired campus network

## Files

- `ysu_login.py`: main script
- `config.example.json`: config template
- `??????.bat`: start daemon mode in a normal window
- `????-??.bat`: start daemon mode minimized
- `??????.bat`: install Windows scheduled task

## Install

### 1. Clone the repository

```powershell
git clone https://github.com/Summerandbreeze/Ysu_netlogin.git
cd Ysu_netlogin
```

### 2. Create your local config

```powershell
copy config.example.json config.json
```

Edit `config.json` and fill in your real account and password:

```json
{
    "userId": "2024XXXXXXXX",
    "password": "your_password_here",
    "service": 3,
    "check_interval": 300,
    "log_file": "login.log"
}
```

## Config

Fields in `config.json`:

- `userId`: your campus network account or student ID
- `password`: your campus network password
- `service`: ISP code
- `check_interval`: interval in seconds for daemon mode
- `log_file`: log file name

`service` values:

- `0`: campus network
- `1`: China Mobile
- `2`: China Unicom
- `3`: China Telecom

## First Test

Run one manual check first:

```powershell
python ysu_login.py once
```

Force a login:

```powershell
python ysu_login.py login
```

Check current status only:

```powershell
python ysu_login.py status
```

If this step does not work, do not install scheduled tasks yet. Fix the config first.

## Automatic Run Options

### Option 1: Daemon mode

Run the script continuously and check every 300 seconds:

```powershell
python ysu_login.py daemon 300
```

You can also double-click:

- `??????.bat`
- `????-??.bat`

If you want it to start with Windows, put `????-??.bat` into your Startup folder.

### Option 2: Windows scheduled task

If you do not want a long-running Python process, use the scheduled task script.

Double-click:

- `??????.bat`

Useful commands:

```powershell
schtasks /query /tn "YSU_???????"
schtasks /run /tn "YSU_???????"
schtasks /delete /tn "YSU_???????" /f
```

## Clash Verge Notes

This project tries to work without manually closing Clash Verge.

Main idea:

- use `curl --noproxy '*'`
- try direct access to the authentication endpoint
- reduce proxy and TUN interference

If login still fails when Clash Verge is enabled, check these points:

1. Make sure the campus authentication domain is not forced through proxy
2. If TUN mode is enabled, add the authentication domain or IP to `DIRECT`
3. Test again with `python ysu_login.py login`
4. Only if needed, temporarily disable TUN as a fallback

## Logs

Default log file:

- `login.log`

Recommended debug steps:

1. Run `python ysu_login.py status`
2. Run `python ysu_login.py login`
3. Open `login.log`
4. Check whether the failure is from account, CAS, portal, or proxy handling

## Security

Do not publish these files:

- `config.json`
- `.login_cookies.txt`
- `login.log`
- any file containing real account, password, cookies, or captured session data

This repository only includes `config.example.json`.

## Disclaimer

This project is for personal use and study only. Please make sure your usage follows your school's network policy.

