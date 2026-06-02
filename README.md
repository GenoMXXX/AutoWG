# wg-watchdog

Локальный `opkg`-пакет для Keenetic с Entware. Следит за выбранным WireGuard-интерфейсом на роутере и перезапускает его, если `rxbytes == 0`, а `txbytes` уже выше порога.

## Возможности

- локальный веб-интерфейс;
- выбор WireGuard-интерфейса;
- настройка `RX_THRESHOLD`, `TX_THRESHOLD`, `POLL_INTERVAL`, `COOLDOWN`;
- задержка старта после загрузки роутера;
- автоподъём упавших процессов;
- без Keenetic API, логина и пароля.

## Установка через репозиторий

```sh
wget -qO- https://genomxxx.github.io/AutoWG/opkg/add_repo.sh | sh
opkg update
opkg install wg-watchdog
```

## Запуск

```sh
/opt/etc/init.d/S99wg-watchdog start
```

## Веб-интерфейс

```text
http://<IP роутера>:18088
```

## Что внутри репозитория

- `docs/opkg/add_repo.sh` - one-line installer для Entware;
- `docs/opkg/Packages` и `Packages.gz` - feed;
- `docs/opkg/wg-watchdog_1.0.0_all.ipk` - пакет;
- `opt/` - файлы самого пакета;
- `CONTROL/` - метаданные `opkg`.
