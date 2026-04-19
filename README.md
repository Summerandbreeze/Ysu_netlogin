# YSU Campus Network Auto Login

[English](https://github.com/Summerandbreeze/Ysu_netlogin/blob/main/README.md) | [Chinese](https://github.com/Summerandbreeze/Ysu_netlogin/blob/main/README.zh-CN.md)

Auto login script for Yanshan University campus network on Windows.

This project is designed for one practical goal: when the campus network drops or requires authentication again, the script checks the network and logs in automatically, while trying to avoid conflicts with Clash Verge.

## What It Does

- Checks whether the network is really online
- Avoids treating the campus login page as normal internet access
- Tries direct portal login first
- Falls back to the old CAS flow if needed
- Works with single-run mode, daemon mode, and Windows scheduled tasks
- Uses `curl --noproxy '*'` to reduce proxy and TUN interference

## Important: Downloading Is Not Enough

After downloading this project, it will **not** start automatically by itself.

You still need to:

1. Create your own `config.json`
2. Fill in your own account, password, and `service`
3. Run a manual test first
4. Choose one auto-run method:
   - daemon mode
   - startup BAT file
   - Windows scheduled task

So the correct order is:

1. Download project
2. Configure project
3. Test manually
4. Enable automatic run

## Requirements

- Windows 10 or Windows 11
- Python 3.9 or later
- `curl.exe` available in the system
- Connected to YSU campus Wi-Fi or wired campus network

## Files

- `ysu_login.py`: main script
- `config.example.json`: config template
- normal-start BAT file: starts daemon mode in a normal window
- minimized-start BAT file: starts daemon mode minimized
- scheduled-task BAT file: installs the Windows scheduled task

## Install With Git

### 1. Clone the repository

```powershell
git clone https://github.com/Summerandbreeze/Ysu_netlogin.git
cd Ysu_netlogin
```

### 2. Create your local config

```powershell
copy config.example.json config.json
```

## Install Without Git

If you cannot use `git clone`, you can still use this project.

### 1. Download ZIP or project folder

- Download ZIP from the GitHub page and extract it
- Or copy the whole project folder to your computer

### 2. Open the project folder in PowerShell

Make sure you are inside the project directory before running commands.

### 3. Create your local config

```powershell
copy config.example.json config.json
```

## Config

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

If this step does not work, do not enable auto-run yet. Fix the config first.

## How To Make It Run Automatically

There are three common ways to make the script run automatically on a Windows computer.

### Option 1: Daemon mode

This keeps the script running continuously and checks every 300 seconds:

```powershell
python ysu_login.py daemon 300
```

This is automatic only while the process is still running.
If you close the terminal or stop the process, automatic checking stops.

You can also start daemon mode by double-clicking one of these files in the project root:

- the BAT file for normal window startup
- the BAT file for minimized startup at boot

### Option 2: Add the minimized BAT file to Windows Startup

Use this when you want the script to start automatically after logging into Windows.

Steps:

1. Make sure your config already works with `python ysu_login.py login`
2. Find the minimized-start BAT file in the project folder
3. Press `Win + R`
4. Enter:

```text
shell:startup
```

5. Put a shortcut of the minimized-start BAT file into that Startup folder

After that, the script will start automatically when you log into Windows.

### Option 3: Install Windows scheduled task

Use this when you do not want a long-running Python terminal window.

Run the scheduled-task BAT file in the project root.
After installation, Windows will launch the script automatically according to the task settings.

You can list all scheduled tasks with:

```powershell
schtasks /query
```

You can also open Task Scheduler and look for the task created by the install BAT file.

## Recommended Setup For New Users

If you are new to this project, use this order:

1. Download the project
2. Create `config.json`
3. Fill in your own account, password, and `service`
4. Run `python ysu_login.py login`
5. Confirm the network really works
6. Then enable one auto-run method

The safest auto-run choice for most users is:

- test manually first
- then use Windows scheduled task

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

