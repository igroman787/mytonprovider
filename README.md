# What is MyTonProvider?

MyTonProvider is a console application that serves as a convenient wrapper around `ton_storage`, `ton_storage_provider`, and `ton_tunnel_provider`. It’s designed specifically for managing provider tasks on Linux.

![MyTonProvider Status](resources/screen.png)

# Module Overview

```bash
telemetry            - Sends telemetry to the server. Helps you rank higher in the providers list.
ton_storage          - Downloads, stores, and serves files over the ADNL protocol. Required by ton_storage_provider.
ton_storage_provider - Signs storage contracts, submits confirmations, and receives payments. Lets you earn by storing others’ files.
ton_tunnel_provider  - Signs traffic-routing contracts. Lets you earn by proxying others’ traffic through your IP address.
```

# Provider Installation (Docker)

1. **Clone the repository and enter the directory:**

   ```bash
   git clone -b docker --single-branch https://github.com/igroman787/mytonprovider.git
   cd mytonprovider
   ```

2. **Fill out `.env`:**

   | Variable                         | Description                                                               | Example value                                             |
   | -------------------------------- | ------------------------------------------------------------------------- | --------------------------------------------------------- |
   | `MYTONPROVIDER_MODULES`          | Modules to install inside the container (comma-separated, **no spaces**). | `ton-storage,ton-storage-provider,auto-updater,telemetry` |
   | `MYTONPROVIDER_STORAGE_PATH`     | **Host** path for provider data (mounted into the container).             | `/var/storage`                                            |
   | `MYTONPROVIDER_STORAGE_COST`     | Your storage price (in TON).                                              | `10`                                                      |
   | `MYTONPROVIDER_SPACE_TO_PROVIDE` | Amount of space you allocate for storage (in GB).                         | `10`                                                      |

3. **Grant permissions on `${MYTONPROVIDER_STORAGE_PATH}` on the host**

   ```bash
   sudo mkdir -p /var/storage
   sudo chown -R 1000:1000 /var/storage
   ```

4. **Build the image:**

   ```bash
   docker-compose build
   ```

5. **Start the service:**

   ```bash
   docker-compose up -d
   ```

6. **Open the provider console:**

   ```bash
   docker exec -it mytonprovider console
   ```

# Telemetry

We recommend enabling telemetry to improve your ranking in the providers list. You can disable it if you prefer.

**Before installation (in `.env`):** remove `telemetry` from `MYTONPROVIDER_MODULES`.

```env
MYTONPROVIDER_MODULES=ton-storage,ton-storage-provider,auto-updater
```

**After installation (in the console):**

```bash
MyTonProvider> set send_telemetry false
```