# Что такое MyTonProvider?
MyTonProvider — консольное приложение, служащее удобной оболочкой для `ton_storage`, `ton_storage_provider` и `ton_tunnel_provider`. Оно специально разработано для задач управления провайдерами в операционной системе Linux.

![MyTonProvider Status](resources/screen.png)

# Описание модулей
```bash
telemetry - Отправляет телеметрию на сервер. Позволяет подняться в списке провайдеров.
ton_storage - Скачивает, хранит и раздает файлы по ADNL протоколу. Необходим для работы ton_storage_provider. 
ton_storage_provider - Заключает контракты на хранение, отправляет подвтерждения и получает оплату. Позволяет получать доход за хранение чужих файлов.
ton_tunnel_provider - Заключает контракты на маршрутизацию трафика. Позволяет получать доход за проксирование чужого трафика через ваш IP адрес.
```

# Установка провайдера (Docker)

1. **Клонируйте репозиторий и перейдите в каталог:**

   ```bash
   git clone -b docker --single-branch https://github.com/igroman787/mytonprovider.git
   cd mytonprovider
   ```

2. **Заполните `.env`:**

    | Переменная                            | Описание                                                                     | Значение (пример)                                         |
    | ------------------------------------- | ---------------------------------------------------------------------------- | --------------------------------------------------------- |
    | `MYTONPROVIDER_MODULES`               | Модули, устанавливаемые внутри контейнера (через запятую, **без пробелов**). | `ton-storage,ton-storage-provider,auto-updater,telemetry` |
    | `MYTONPROVIDER_STORAGE_PATH`          | Путь на **хосте** для данных провайдера (маунтится в контейнер).             | `/var/storage`                                            |
    | `MYTONPROVIDER_STORAGE_COST`          | Ваша ставка за хранение (в TON).                                             | `10`                                                      |
    | `MYTONPROVIDER_SPACE_TO_PROVIDE`      | Объём, который вы отдаёте под хранение (в ГБ).                               | `10`                                                      |

3. **Выдайте права на `${MYTONPROVIDER_STORAGE_PATH}` на хосте**

   ```bash
   sudo mkdir -p /var/storage
   sudo chown -R 1000:1000 /var/storage
   ```

4. **Соберите образ:**

   ```bash
   docker-compose build
   ```

5. **Поднимите сервис:**

   ```bash
   docker-compose up -d
   ```

6. **Откройте консоль провайдера:**

   ```bash
   docker exec -it mytonprovider console
   ```

# Телеметрия

Мы рекомендуем включать телеметрию для повышения себя в списке провайдеров. Однако при желании вы можете отключить телеметрию.

**До установки (в `.env`):** удалите `telemetry` из `MYTONPROVIDER_MODULES`.

```env
MYTONPROVIDER_MODULES=ton-storage,ton-storage-provider,auto-updater
```

**После установки (в консоли):**

```bash
MyTonProvider> set send_telemetry false
```