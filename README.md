# FreeXR-Bot
FreeXR Discord Bot

## Changelog

### v2 changelog:

#### General
- **All commands are now hybrid commands** (`@bot.hybrid_command()`), supporting both prefix and slash usage. Thanks @Anonymous941 !
- You can now run the bot with `-t TOKEN` to specify the Discord bot token.
- **Improved error handling**: 
  - Unauthorized command usage now pings the user and says they are not authorized.
  - Missing required arguments are now reported to the user.
- **Fixed`.replies_cmd` command** (replaced with a single `replies` hybrid command)
- **Counting now support arithmetics**, (and SPOILER: it's not just eval())
  - Bot now uses arithmeval, python library that gives bot ability to do basic math ( and not only )
  - Now you can use Addition (+), True division (/), Floor division (//), Modulus (%), Multiplication (*), Exponentiation (**), Subtraction (-), Logical AND (and), Logical OR (or), Logical NOT (not), and even pi (π), e, tau (τ), the golden ratio (φ), Euler-Mascheroni's gamma (gamma), the speed of light (c), Newton's gravitational constant (G), and Planck's constant (h). (IDK why you would use them)

#### Device Management
- **New persistent device system**:
  - `devices` lists your devices or another user's devices.
  - `deviceadd` adds a device using a Discord modal form (slash command only).
  - `deviceremove <id>` removes a device by its per-user index.
  - `deviceinfo <user> <id>` shows info for a specific device.
  - Devices are stored in data/devices.json

Don't know what this would be used for... :)

#### Regex Management
- **Regex block command now uses a modal** (slash command only) for adding new regex patterns.
- **Regex list, toggle, and unblock commands now use 1-based indices** for user-facing commands (internally adjusted to 0-based). This was one of the earliest bugs present when we first implemented the regex system.

#### Replies System
- **Removed explicit `replies` handling from `on_message`**, now handled by the hybrid command.

#### Miscellaneous
- **Update and hotupdate commands**:
  - `update` pulls the whole repo and restarts the bot.
  - `hotupdate` pulls the repo and reloads replies without restarting, replacing the old `updatereplies` command.
- **Separate files**:
  - One-file bot code was split into multiple files.
  - Adding new features and reviewing them is now easier.
- **General code cleanup and refactoring** for clarity and maintainability.

Thanks to all of FreeXR supporting, you 667 members all rock <3
